# API UI — Personalizzazioni liste (Django)

## Scopo

Esporre via HTTP la configurazione effettiva di una lista per l'utente
autenticato (cascata preset + permessi) e gestire la sua preferenza
personale (UPSERT/DELETE). Endpoint trasversali consumati da tutte le
viste del frontend che usano il componente `<ListaConfigurabile>`.

## Contesto

Strato di presentazione del refactor `sviluppo-personalizzazioni-liste.md`
(Blocchi A+B+C atterrati 2026-05-06/07). Lo schema DB `ui` ospita 6
tabelle (`lista_definizione`, `lista_colonna`, `lista_preset`,
`lista_preset_colonna`, `lista_preferenza_utente`, `lista_colonna_permesso`)
e la funzione `ui.fn_resolve_lista_config(VARCHAR, INTEGER, BIGINT)` che
applica:

1. cascata preferenza utente -> preset di ruolo (priorita ASC) ->
   preset di emittente -> preset di sistema -> catalogo grezzo;
2. merge automatico delle nuove colonne aggiunte al catalogo dopo
   l'ultimo salvataggio della preferenza (con `visibile=false`);
3. normalizzazione colonne obbligatorie (`identificatore`/`azione`
   forzate a `visibile=true`);
4. filtro autorizzativo (deny-list per non sensibili, allow-list per
   sensibili) via `script.fn_get_profili_accesso_applicabili` filtrata
   per la veste corrente (GUC `app.ruolo_applicativo`).

Il backend Django (`apps.ui`) e' un wrapper sottile: tutta la logica
di dominio vive nel DB. La meta-API e' trasversale ai domini funzionali
(non legata a un'`area_funzionale` di business): tutte le view usano
`DomainAPIView` con `skip_area_check = True`. JWT obbligatorio su tutti
gli endpoint; lo scope dati per-utente e' implicito (la fn DB filtra
sull'`auth_user_id` e i profili applicabili).

`emittente_fiscale_id` non e' un parametro di input HTTP: e' derivato
1:1 lato service via `PermissionResolver.get_emittente_for_user`
(refactor operatore-emittenti, una sola riga in `config.user_emittenti_fiscali`).
Per admin globale (0 righe) -> `None` -> la fn DB ricade sul preset di
sistema o sul catalogo grezzo.

---

## Endpoint

### 1. Risolvi configurazione lista

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/liste/{codice}/config/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path parameter:
  - `codice` (string) — codice della lista come definito in
    `ui.lista_definizione.codice`. Convenzione `<schema>.<entita>` o
    `<schema>.<entita>:<contesto>` (es. `anagrafiche.clienti`,
    `anagrafiche.clienti:picker`).
- Query param:
  - `emittente_esplicito` (int, opzionale) — l'emittente già fissato dal contesto
    che apre la lista (per esempio un tab dentro il drawer di un emittente). Se c'è,
    la lista non è ambigua e `richiede_scelta_emittente` è `false`. Un valore non
    intero o ripetuto è trattato come assente.

#### Output

- `200`:

```json
{
  "data": {
    "colonne": [
      {
        "codice": "ragione_sociale",
        "ordine": 1,
        "larghezza": 240,
        "visibile": true,
        "fissata": true,
        "esportabile": true,
        "tipo_colonna": "identificatore"
      },
      {
        "codice": "partita_iva",
        "ordine": 2,
        "larghezza": 130,
        "visibile": true,
        "fissata": false,
        "esportabile": true,
        "tipo_colonna": "informazione"
      }
    ],
    "ordinamento": [{"col": "ragione_sociale", "dir": "asc"}],
    "filtri": {"attivo": true},
    "pagina_dimensione": 25,
    "colonne_nuove": 0,
    "ricerca_full": true,
    "richiede_scelta_emittente": false
  },
  "meta": {"request_id": "..."}
}
```

Campi dell'oggetto colonna:

- `codice` — riferimento stabile a `ui.lista_colonna.codice`
- `ordine` — posizione nella tabella renderizzata (intero crescente)
- `larghezza` — pixel suggeriti (override del preset/preferenza, fallback
  a `ui.lista_colonna.larghezza_default`)
- `visibile` — se `false`, la colonna e' nel pool ma non mostrata di
  default; appare nella modale di personalizzazione
- `fissata` — frozen column (non scrolla orizzontalmente). Sempre `true`
  per `tipo_colonna='identificatore'`
- `esportabile` — se `false`, la colonna e' visibile a video ma esclusa
  dall'export (deriva da livello permesso `LETTURA` o da
  `lista_colonna.esportabile=false` per `tipo_colonna='azione'`)
- `tipo_colonna` — uno tra `identificatore`, `informazione`, `azione`.
  Il FE disabilita il toggle visibilita' nella modale per
  `identificatore` e `azione`.

Campi top-level:

- `colonne_nuove` — quante colonne del catalogo non erano presenti nella
  preferenza salvata (per il badge UX "N nuove colonne disponibili")
- `ordinamento` / `filtri` / `pagina_dimensione` — stato derivato dalla
  cascata (preferenza > preset di ruolo > preset di emittente > preset
  di sistema > la misura di default `PAGINA` del catalogo
  `ui.misure_pagina`). ⭐ Dal 2026-09-30 `pagina_dimensione` e' **sempre
  una misura del catalogo**: quella scelta se ammessa, altrimenti il
  default — mai `NULL`, mai un numero che il paginatore non offre
- `ricerca_full` — `true` se la lista ha, **per l'utente corrente**, almeno
  una colonna in cui la ricerca libera cerca (`ricercabile_full = t`,
  attiva, non `BLOCCATO` per i permessi di colonna). Il frontend mostra la
  casella di ricerca **solo** se e' vera: una casella senza colonne accese non
  troverebbe niente. Letta da `ui.fn_lista_colonne_ricerca_full`, la stessa
  sede del BB `add_ricerca_full_condition` (dal 2026-09-23,
  brief-be-ricerca-full-liste-residue §7-bis). ⚠️ Solo in questo endpoint
  (`UiService.get_lista_config_per_video`): la configurazione che leggono
  l'export e la modale di personalizzazione non la porta, e non paga la query

- `richiede_scelta_emittente` — `true` se l'operatore deve scegliere un
  emittente prima di vedere la lista: la lista ha un perimetro emittente, non è
  certificata multi-emittente, non c'è un `emittente_esplicito` e il perimetro
  effettivo dell'utente ha più di un emittente. Lo calcola il backend
  (`perimetro_emittente.richiede_scelta_emittente`, lo stesso BB del cancello
  `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` sulle rotte dati): il frontend non lo
  ricalcola

Errori:

- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — `codice` non esiste in
  `ui.lista_definizione` oppure `attivo=false`
- `400` `E_UI_GENERIC_FAILED` — DatabaseError generico durante la
  risoluzione (caso eccezionale, log a DB)
- `500` `E_UI_CHIAMATA_NON_VALIDA` (classe `TECNICO`, dal 2026-09-24) — il
  contesto di sessione della richiesta (GUC `app.current_user_id`) è vuoto o
  nomina un utente diverso da quello autenticato. La configurazione risponde
  per l'utente della chiamata, `ricerca_full` e la ricerca vera per quello
  della GUC: se divergessero, la casella direbbe una cosa e la ricerca ne
  farebbe un'altra, senza errore. In una richiesta HTTP le due fonti
  coincidono per costruzione (`JwtAuditAuthentication`), quindi a video non
  compare mai: segnala un chiamante rotto. Contesto a diario: `lista_codice`,
  `auth_user_id`, `utente_di_sessione`. Brief-be-ricerca-full-liste-residue §12

#### Note

- Idempotente, no side effect. Cache lato FE con ETag e' un'evoluzione
  pianificata (vedi WIP §10.3).
- Non accetta `emittente_fiscale_id` come query param: e' derivato
  internamente dall'utente. L'unico parametro di perimetro è
  `emittente_esplicito`, che non cambia la configurazione ma solo
  `richiede_scelta_emittente`.

---

### 2. Catalogo colonne (per modale di personalizzazione)

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/liste/{codice}/catalogo/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path parameter: `codice` (vedi §1)

#### Output

- `200`:

```json
{
  "data": {
    "colonne": [
      {
        "id": 1,
        "codice": "ragione_sociale",
        "etichetta": "Ragione sociale",
        "etichetta_estesa": "Ragione sociale del cliente",
        "campo_sorgente": "ragione_sociale",
        "tipo_colonna": "identificatore",
        "tipo_dato": "string",
        "formato": null,
        "larghezza_default": 240,
        "ordine_default": 10,
        "allineamento": "left",
        "gruppo": "Anagrafica",
        "gruppo_ordine": 10,
        "filtrabile": true,
        "ordinabile": true,
        "esportabile": true,
        "ricercabile_full": true,
        "sensibile": false,
        "attivo": true
      }
    ]
  },
  "meta": {"request_id": "..."}
}
```

I metadati ricchi (etichetta, etichetta_estesa, gruppo, gruppo_ordine,
formato, ordine_default, ecc.) servono al frontend per renderizzare la
modale: raggruppamento collassabile per `gruppo`/`gruppo_ordine`,
tooltip da `etichetta_estesa`, ordinamento di default per
`ordine_default`.

L'output **filtra le colonne BLOCCATE** per il profilo dell'utente:
quelle escluse da `ui.fn_resolve_lista_config` (deny-list non sensibili
+ allow-list sensibili) non compaiono nemmeno nella modale, perche' la
modale non puo' offrire l'attivazione di una colonna proibita.

Errori:

- `401`, `404`, `400` — stessi codici di §1 (la view delega a
  `UiService.get_lista_config` per la risoluzione 404+permessi prima di
  arricchire i metadati).

---

### 3. UPSERT preferenza utente

#### Input

- Metodo: `PUT`
- Path canonico: `/api/v1/ui/liste/{codice}/preferenza/`
- Header sicurezza:
  - `Authorization: Bearer <access_token>`
  - `Idempotency-Key: <uuid-stringa>` — **obbligatorio** (cfr. policy
    api.md su modifiche di stato)
- Path parameter: `codice` (vedi §1)
- Body JSON (tutti i campi opzionali; whitelist rigida — chiavi extra
  rifiutate):

```json
{
  "colonne": [
    {
      "codice": "ragione_sociale",
      "ordine": 1,
      "larghezza": 240,
      "visibile": true,
      "fissata": true
    },
    {"codice": "partita_iva", "ordine": 2, "visibile": true}
  ],
  "ordinamento": [{"col": "ragione_sociale", "dir": "asc"}],
  "filtri": {"attivo": true},
  "pagina_dimensione": 50
}
```

Whitelist root payload: `colonne`, `ordinamento`, `filtri`,
`pagina_dimensione`. Whitelist colonna: `codice`, `ordine`, `larghezza`,
`visibile`, `fissata`. Vincoli:

- `codice` (string) — obbligatorio; deve essere presente nel catalogo
- `ordine`, `larghezza` (int positivo) — opzionali
- `visibile`, `fissata` (bool stretto) — opzionali; non accetta `"true"`
  o `1`
- `pagina_dimensione` (int) — una delle misure del catalogo
  `ui.misure_pagina` (endpoint 6). ⭐ Il backend ne controlla solo la
  **forma**; l'ammissibilita' la decide il guard a DB, e una misura fuori
  catalogo risponde `400 E_UI_MISURA_PAGINA_NON_AMMESSA`. ⛔ Fino al
  2026-09-30 il service applicava un suo tetto (`MAX_LIMIT`, 200): una
  seconda regola, diversa dal catalogo, che ammetteva 37
- `ordinamento` — lista di oggetti, formato trasparente al BE (decisione
  congiunta col componente Vue, vedi WIP §10.1.2)
- `filtri` — oggetto, formato trasparente al BE

#### Output

- `200`:

```json
{
  "data": {
    "id": 99,
    "preset_base_id": 5
  },
  "meta": {"request_id": "..."}
}
```

- `id` — PK della riga in `ui.lista_preferenza_utente`
- `preset_base_id` — id del preset di base risolto al momento del
  salvataggio (`null` se l'utente partiva dal catalogo grezzo). Lo
  snapshot del `data_update` di quel preset e' memorizzato in
  `lista_preferenza_utente.preset_base_data_update` per il badge
  "preset aggiornato" (DEF-2).

Errori:

- `400` `E_IDEMPOTENCY_KEY_REQUIRED` — header `Idempotency-Key` mancante
- `400` `E_UI_PREFERENZA_VALIDAZIONE` — payload non whitelisted, tipi
  errati, ecc. Il dettaglio indica esattamente quale chiave/colonna ha
  violato il vincolo.
- `400` `E_UI_MISURA_PAGINA_NON_AMMESSA` — `pagina_dimensione` non e' una
  misura del catalogo (dal guard a DB; il messaggio elenca le ammesse)
- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — codice lista non esistente o non attivo

#### Note

- L'UPSERT usa `ON CONFLICT (auth_user_id, lista_id) DO UPDATE`: stessa
  chiamata aggiorna la preferenza esistente.
- `preset_base_data_update` viene aggiornato a ogni salvataggio:
  l'utente che salva risolve implicitamente l'eventuale notifica
  "preset aggiornato".
- L'`Idempotency-Key` strong mode (`DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1`)
  fa replay della risposta sulla stessa key entro la TTL di
  `dbops.idempotency_keys`.

---

### 4. DELETE preferenza utente

#### Input

- Metodo: `DELETE`
- Path canonico: `/api/v1/ui/liste/{codice}/preferenza/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path parameter: `codice` (vedi §1)
- Body: nessuno

#### Output

- `200`:

```json
{
  "data": {"deleted": true},
  "meta": {"request_id": "..."}
}
```

`deleted=true` se la preferenza esisteva ed e' stata eliminata,
`false` se non esisteva (idempotenza). Al prossimo `GET .../config`
l'utente parte dal preset di ruolo / emittente / sistema / catalogo
grezzo (cascata standard).

Errori:

- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — codice lista non esistente
  (caso patologico: protezione contro path errati; non e' un errore
  business reale per l'utente)

---

### 5. POST preferenza/ignore-preset-update (DEF-2)

#### Scopo

Tombstone "Ignora banner preset aggiornato": setta
`ui.lista_preferenza_utente.preset_aggiornato_ignored_at = NOW()` sulla
preferenza utente per `(request.user, codice)`. Il flag
`preset_aggiornato` ritornato da `ui.fn_resolve_lista_config` torna
`false` finche' il preset non viene modificato di nuovo
(`preset.data_update > ignored_at`).

L'endpoint chiude la conversazione "l'amministratore ha aggiornato il
preset del tuo ruolo, vedi novita' / ignora": "Vedi novita'" si chiude
naturalmente al successivo save preferenza (lo snapshot
`preset_base_data_update` si riallinea); "Ignora" usa questo endpoint
per nascondere il banner senza modificare la configurazione utente.

#### Input

- Metodo: `POST`
- Path canonico: `/api/v1/ui/liste/{codice}/preferenza/ignore-preset-update/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Header obbligatorio: `Idempotency-Key: <uuid>` (allineamento al pattern POST `handle_post_json`, strong mode replay su `dbops.idempotency_keys`)
- Path parameter: `codice` (vedi §1)
- Body: nessuno

#### Output

- `200`:

```json
{
  "data": {"ignored": true},
  "meta": {"request_id": "..."}
}
```

Errori:

- `400` `E_IDEMPOTENCY_KEY_REQUIRED` — header `Idempotency-Key` mancante
- `401` — JWT mancante o non valido
- `404` `E_UI_LISTA_NON_TROVATA` — codice lista non esistente
- `404` `E_UI_PREFERENZA_NON_TROVATA` — l'utente non ha ancora una
  preferenza salvata sulla lista (caso patologico: il banner non
  sarebbe visibile, ma chiamata diretta da retry/script viene
  rifiutata)

#### Note DEF-2

- **Idempotency-Key**: obbligatoria per coerenza con il pattern POST
  (api.md). Il replay strong mode garantisce che retry FE non duplichino
  side-effect anche se `now()` viene comunque sovrascritto in modo
  benigno.
- **Reset automatico tombstone**: il trigger
  `trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts` azzera
  anche `preset_aggiornato_ignored_at` quando cambia `preset_base_id`
  (cambio preset di base = relazione utente-preset resettata, il
  tombstone storico riferisce al vecchio preset).
- **Riapparizione banner**: il banner torna visibile alla prossima
  modifica del preset (`preset.data_update > ignored_at`). Pattern by
  design: l'utente che "ignora una volta" non perde visibilita' sulle
  future modifiche.

---

### 6. GET misure-pagina

#### Scopo

Le misure «righe per pagina» che **ogni** paginatore dell'applicazione
offre, e i due default, lette da `ui.fn_get_misure_pagina()` (catalogo
`ui.misure_pagina`, sede unica per DB, backend e frontend — decisioni di
Tid del 2026-09-29). Non sono dentro la configurazione di una lista perche'
le usano anche tabelle grezze, dialog e cruscotti. Il frontend le legge
**una volta per sessione**, dal guard del router, prima di aprire
qualunque pagina dell'operatore (BB `core/misurePagina.js`).

#### Input

`GET /api/v1/ui/misure-pagina/` — nessun parametro. JWT obbligatorio.

#### Output

- `200`:

```json
{
  "data": {
    "misure": [10, 25, 50, 100],
    "default_compatta": 10,
    "default_pagina": 25
  },
  "meta": {"request_id": "..."}
}
```

- `misure` — in ordine crescente (l'ordine del selettore)
- `default_compatta` — la misura di partenza delle liste in drawer e dialog
- `default_pagina` — quella delle liste a pagina intera, e il ripiego del
  resolver quando nessuno ha scelto

Errori:

- `401` — JWT mancante o non valido
- `500` `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` (`TECNICO`) — il catalogo non
  ha la riga di uno dei due default: anomalia di seed, non un valore vuoto

---

## Regole

- **Permessi**: `skip_area_check = True` su tutte le view. JWT
  obbligatorio. Lo scope dati per-utente e' applicato dalla fn DB
  (filtri sui profili applicabili dell'utente).
- **Multi-veste**: la veste corrente e' letta dalla GUC
  `app.ruolo_applicativo` (propagata da `JwtAuditAuthentication`).
  Utente con identita' multi-veste (es. OPERATORE+CLIENTE_PORTALE su
  stessa email) vede preset/permessi della sola veste del JWT corrente
  (DB-4 landed 2026-05-07).
- **Cascata preset di ruolo**: ordinata per `priorita ASC` (AD_HOC=1
  prevale su REPARTO/PORTALE=2). DB-3 landed 2026-05-07.
- **Eliminazione preset di base**: la FK `preset_base_id` e'
  `ON DELETE SET NULL` (DB-2 landed). Trigger DB
  `trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd` azzera
  anche `preset_base_data_update`. Il FE deve verificare
  `preset_base_id IS NOT NULL` prima di mostrare il badge "preset
  aggiornato".
- **Veste GUC corrotta**: il cast in fn DB e' avvolto in `EXCEPTION
  WHEN invalid_text_representation THEN NULL` -> fallback "tutte le
  vesti" (legacy) invece di propagare eccezione (deviazione team DB
  rispetto al brief originale).

## Dipendenze DB

- Tabelle: `ui.lista_definizione`, `ui.lista_colonna`, `ui.lista_preset`,
  `ui.lista_preset_colonna`, `ui.lista_preferenza_utente`,
  `ui.lista_colonna_permesso`, `ui.misure_pagina`
- Funzioni: `ui.fn_resolve_lista_config`, `ui.fn_get_misure_pagina`,
  `script.fn_get_profili_accesso_applicabili`,
  `script.fn_resolve_emittente_for_user` (via Python
  `PermissionResolver.get_emittente_for_user`)
- Trigger: `trgfn_ui_lista_definizione_a10_valida_vista_sql`,
  `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`,
  `trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd`

## Building block backend usati

- [`apps.core.api.base_views.DomainAPIView`](../../core/manual/api-domain-conventions.md)
  con `skip_area_check=True`
- [`apps.core.api.endpoint_helpers.handle_post_json`](../../core/manual/api_endpoint_helpers.md)
  con `require_idempotency_key=True` (PUT preferenza)
- [`apps.core.services.payload_helpers.PayloadValidator`](../../core/manual/payload-validation-api.md)
  per la whitelist JSONB
- [`apps.core.services.permissions_resolver.PermissionResolver.get_emittente_for_user`](../../core/manual/permissions_resolver.md)
  per la derivazione 1:1 user->emittente
- [`apps.core.services.error_manager.ErrorManager`](../../core/manual/error-handling-api.md)
  per gli errori strutturati

## Codici errore registrati

In `apps/core/services/error_policies.py`:

| Codice | HTTP | UI action | Origine |
| ------ | ---- | --------- | ------- |
| `E_UI_LISTA_NON_TROVATA` | 404 | `show_empty_state` | Service (lista inesistente o `attivo=false`) + fn DB |
| `E_UI_VISTA_SQL_NON_TROVATA` | 400 | `show_error_banner` | Trigger B1 (admin only — seed/import) |
| `E_UI_CAMPO_SORGENTE_NON_TROVATO` | 400 | `show_error_banner` | Trigger B2 (admin only) |
| `E_UI_PREFERENZA_VALIDAZIONE` | 400 | `highlight_form_fields` | Service write (whitelist/tipi) |
| `E_UI_GENERIC_FAILED` | 400 | `show_error_banner` | Service (DatabaseError non riconosciuto) |
| `E_UI_CHIAMATA_NON_VALIDA` | 500 | `show_error_banner` | Service (`get_lista_config_per_video`: contesto di sessione ≠ utente della chiamata) |
| `E_UI_MISURA_PAGINA_NON_AMMESSA` | 400 | default `DATO_ERRATO` | Guard DB su preset e preferenza (misura fuori catalogo) |
| `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` | 500 | default `TECNICO` | fn DB (`ui.fn_misura_pagina_default`: il catalogo non ha il default) |

## Note di migrazione

- App `apps.ui` registrata in `INSTALLED_APPS` di
  [zeroerp_backend/settings.py](../../../../backend/zeroerp_backend/settings.py).
- Routing: `path("api/v1/ui/", include("apps.ui.api.urls"))` in
  [zeroerp_backend/urls.py](../../../../backend/zeroerp_backend/urls.py).
- 26 test unit (17 service + 6 API + 3 helper) in
  `apps/ui/tests/`. Tutti basati su `SimpleTestCase`/`JwtMockedApiTest`
  con repository mockato (CI senza DB reale).
- Brief team DB DB-1..DB-4 atterrato 2026-05-07
  (vedi [`brief-db-ui-personalizzazioni-liste.md`](../../../dev/work-done/brief-db-ui-personalizzazioni-liste.md)).
