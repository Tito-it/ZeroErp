# API Definizioni Workflow versionate (Django)

## Scopo

Espone l'amministrazione delle **edizioni di workflow versionate**
(`pratiche.workflow_definizioni`): elenco con drift, dettaglio strutturale
(step + figli + archi), azioni di ciclo di vita (fork / nuova versione / pubblica)
ed editing strutturale della BOZZA (CRUD degli step). Superficie **super-admin**.

## Contesto

Fase 2 del brief
[brief-design-workflow-definizioni-versionate](../../../dev/work-in-progress/brief-design-workflow-definizioni-versionate.md).
Gate app-layer: **`AdminAPIView`** (solo super-admin). **DB-first**: tutta la logica
di dominio (copia edizione, invarianti, immutabilità, validazione pubblicazione) vive
nelle fn/guard DB `SECURITY DEFINER`; il BE è un wrapper sottile che fa solo guard di
bordo sugli id, ownership e **mapping dei DatabaseError noti** in `ServiceError`
parlanti (marker in `pratiche_service._KNOWN_DB_ERROR_MARKERS`).

Ciclo di vita di un'edizione: `BOZZA` (editabile) → `PUBBLICATA` (unica per scope
`tipo_prestazione × emittente`, immutabile strutturalmente) → `RITIRATA`. Il **preset**
è l'edizione con `emittente_fiscale_id = NULL`. Invariante: **≤1 BOZZA per scope**.

```text
GET    /api/v1/pratiche/definizioni/                              (ApiDefinizioniWorkflow)
GET    /api/v1/pratiche/definizioni/<id>/                         (ApiDefinizioneDettaglio)
POST   /api/v1/pratiche/definizioni/<id>/fork/                    (ApiDefinizioneFork)
POST   /api/v1/pratiche/definizioni/<id>/nuova-versione/          (ApiDefinizioneNuovaVersione)
POST   /api/v1/pratiche/definizioni/<id>/pubblica/               (ApiDefinizionePubblica)
POST   /api/v1/pratiche/definizioni/<id>/steps/                   (ApiDefinizioneSteps)
PATCH  /api/v1/pratiche/definizioni/<id>/steps/<step_id>/         (ApiDefinizioneStepDetail)
DELETE /api/v1/pratiche/definizioni/<id>/steps/<step_id>/         (ApiDefinizioneStepDetail)
```

Catena: `views_definizioni.py` → `definizioni_service` → `DefinizioniRepository`
(+ fn DB `fn_fork/nuova_versione/pubblica_definizione` per il ciclo di vita).

---

## `GET /definizioni/` — elenco edizioni con drift

**Query params** (opzionali):

- `tipo_prestazione_id` (int): filtra per tipo.
- `emittente_fiscale_id` (int): filtra per emittente; assente = tutte, preset inclusi.

**Output** `data.results[]` — una riga per edizione:

```json
{
  "id": 419, "tipo_prestazione_id": 9004,
  "tipo_prestazione_descrizione": "…", "emittente_fiscale_id": 44,
  "emittente_display": "…", "versione": 3, "stato": "BOZZA",
  "descrizione": "…", "preset_origine_id": 7, "versione_origine": 1,
  "drift": { "versioni_indietro": null, "preset_corrente_id": null,
             "versione_preset_corrente": null }
}
```

`drift` è `null` (in-sync) o valorizzato quando il preso d'origine ha una PUBBLICATA
più recente di `versione_origine` (banner "preset aggiornato").

## `GET /definizioni/<id>/` — dettaglio strutturale

Alimenta la UI di editing. **Output** `data`:

```json
{
  "definizione": { …stessi campi della lista, con `drift` annidato… },
  "steps": [
    { "id": 9666, "codice": "RICHIESTA_CLIENTE", "descrizione": "…",
      "sequenza": 10, "obbligatorio": true, "direzione": "ENTRATA",
      "attivo": true, "modalita_esito": "CONTESTUALE", "esito_default": null,
      "chiude_pratica": false, "ripetibilita": "SE_NON_POSITIVO",
      "azione_ui_id": null, "azione_ui_key": null,
      "handler_id": null, "handler_key": null, "has_handler": false,
      "canali": [ { "id": …, "canale_id": …, "canale_codice": "WEB",
                    "canale_descrizione": "…", "canale_codice_interno": "…",
                    "attivo": true } ],
      "handler_eventi": [ { "id": …, "evento": "…", "esito_richiesto": null,
                            "handler_id": …, "handler_key": "…",
                            "sequenza": 0, "attivo": true } ],
      "competenze": [ { "id": …, "unita_organizzativa_id": …,
                        "unita_organizzativa_descrizione": "…",
                        "risorsa_umana_id": …, "risorsa_umana_display": "…",
                        "attivo": true } ] }
  ],
  "archi": {
    "prerequisiti": [ { "id": …, "template_flusso_id": 9667,
                        "prerequisito_id": 9666, "esito_richiesto": "POSITIVO" } ],
    "formule_tempo": [ { "id": …, "template_flusso_da_id": …,
                         "template_flusso_a_id": …, "giorni_esecuzione": …,
                         "giorni_warning": …, "giorni_critico": …,
                         "attivo": true, "descrizione": "…" } ],
    "regole_generazione": [ { "id": …, "template_flusso_origine_id": …,
                              "template_flusso_dest_id": …,
                              "tipo_prestazione_dest_id": …,
                              "esito_richiesto": null, "auto": …,
                              "attivo": true, "descrizione": "…" } ]
  }
}
```

Note contratto:

- I figli per-nodo (`canali`, `handler_eventi`, `competenze`) sono **annidati sotto lo
  step**; gli archi sono al livello edizione e referenziano gli step **per id** (il FE
  mappa a `codice` via l'array `steps` dello stesso payload).
- `handler_params` (jsonb) e `meta` sono esclusi da questo contratto (config di dettaglio,
  anello di editing dedicato).
- `regole_generazione`: il `template_flusso_dest_id` può appartenere a un'altra edizione
  (generazione cross-pratica) → id grezzo, non risolto qui.
- **404** `E_DEFINIZIONE_NOT_FOUND` se l'id non esiste.

## `POST /definizioni/<id>/fork/` — crea l'edizione BOZZA di un emittente

**Body**: `{ "emittente_fiscale_id": <int> }`. Header `Idempotency-Key` **obbligatorio**.
Copia (via `fn_fork_definizione`) header + step + figli in una nuova BOZZA d'emittente
con provenance (`preset_origine_id`/`versione_origine`). **Output**:
`{ "definizione_id": <nuovo_id> }`.

## `POST /definizioni/<id>/nuova-versione/` — nuova versione BOZZA

Body vuoto `{}`. `Idempotency-Key` obbligatorio. Deriva una nuova BOZZA **dalla
PUBBLICATA corrente dello scope** (per editarla senza toccare la pubblicata).
**Output**: `{ "definizione_id": <nuovo_id> }`.

## `POST /definizioni/<id>/pubblica/` — pubblica una BOZZA

Body vuoto `{}`. `Idempotency-Key` obbligatorio. `fn_pubblica_definizione` valida la
BOZZA (≥1 step attivo, nessun ciclo di prerequisiti) e la porta a PUBBLICATA, ritirando
la precedente PUBBLICATA dello scope (→ RITIRATA), atomicamente.
**Output**: `{ "definizione_id": <id> }`.

## `POST /definizioni/<id>/steps/` — crea uno step (BOZZA)

Editing strutturale (Slice 2). **Body** — campi **core** (gli altri hanno DEFAULT DB):

| Campo | Obbl. | Note |
|---|---|---|
| `codice` | ✅ | univoco per definizione |
| `descrizione` | ✅ | |
| `sequenza` | — | default `0` |
| `obbligatorio` | — | default `false` |
| `direzione` | — | default `INTERNA` (enum CHECK DB) |
| `modalita_esito` | — | default `MANUALE` (enum CHECK DB) |
| `esito_default` | — | nullable |

`definizione_id` e `tipo_prestazione_id` sono impostati dal BE (non dal client). Gli enum
(`direzione`, `modalita_esito`) sono validati dai CHECK DB, non duplicati in Python.
**Output**: `{ "step_id": <id> }`.

## `PATCH /definizioni/<id>/steps/<step_id>/` — aggiorna campi core di uno step

Body: uno o più campi core (stesso set del create; `sequenza` per il riordino). Ownership
atomica su `(id, definizione_id)`. **Output**: `{ "step_id": <id> }`.

## `DELETE /definizioni/<id>/steps/<step_id>/` — cancella (hard) uno step

Hard delete (una BOZZA non ha pratiche pinnate). Ownership su `(id, definizione_id)`.
**Output**: `{ "deleted": true }`.

---

## Immutabilità e scope

Le operazioni di editing (create/patch/delete step) **passano solo su edizioni
editabili** (BOZZA e preset PUBBLICATO): sulle edizioni **per-emittente già emesse**
(PUBBLICATA o RITIRATA) i guard DB bloccano la modifica strutturale (la sola
`descrizione` resta correggibile). Il BE non replica il controllo: lo riceve dal DB e lo
traduce in un errore parlante.

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_INVALID_ID` | 400 | id ≤ 0 / mancante |
| `E_VALIDATION_INPUT` | 400 | `codice`/`descrizione` mancanti (create) o payload PATCH senza campi core |
| `E_DEFINIZIONE_NOT_FOUND` | 404 | definizione o step inesistente / fuori scope (ownership) |
| `E_TEMPLATE_CODICE_DUPLICATO` | — | `codice` step già presente nella definizione |
| `TEMPLATE_DEFINIZIONE_CONGELATA` | — | editing di un'edizione per-emittente già emessa |
| `DEFINIZIONE_BOZZA_ESISTENTE` | — | fork / nuova-versione con una BOZZA già aperta nello scope |
| `DEFINIZIONE_NO_PUBBLICATA` | — | nuova-versione da sorgente non PUBBLICATA |
| `DEFINIZIONE_NON_PUBBLICABILE` | — | pubblica di una BOZZA senza step attivi o con ciclo di prerequisiti |

I codici senza `E_` sono marker verbatim del catalogo DB (`config.messaggi_errore`),
intercettati per substring stabile in `_KNOWN_DB_ERROR_MARKERS` e ripubblicati con lo
stesso codice; l'HTTP status segue la policy in `error_policies.py` (i guard di dominio DB
si presentano come banner, `ui_action=show_error_banner`).
