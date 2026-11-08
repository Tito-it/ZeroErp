# Linee guida API

> Destinatari: sviluppatori backend di Zero ERP
> **Ultimo aggiornamento**: 25 ottobre 2026
>
> Vedi anche:
>
> * [Catalogo building block backend](backend/catalogo-building-block-backend.md) — inventario completo componenti riutilizzabili
> * [Policy ricerca e paginazione](/dev/Policy-ricerca-e-paginazione(API-DB))
> * [Messaggi di errore e log](/guide/Messaggi-di-Errore-e-Generazione-Log)
> * [Guida fatturazione](/guide/fatturazione) — esempio completo di dominio con API

---

## Principi di progettazione

Zero ERP espone **azioni di dominio**, non operazioni CRUD generiche.

| Principio              | Regola                                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| DB-first               | Il database e` l'autorita` su stato, vincoli e regole. L'API non replica logica gia` garantita dal DB                 |
| Azioni atomiche        | Ogni endpoint POST rappresenta un'unita` di lavoro completa, eseguita in un'unica transazione                         |
| Separazione read/write | GET = consultazione (nessun side-effect). POST = comando (modifica stato). PATCH = aggiornamento parziale controllato |
| Nessun CRUD esposto    | Non si usano ModelViewSet ne` router DRF automatici. Ogni endpoint e` una APIView esplicita                           |

---

## Grammatica URL — Regole vincolanti

### CRUD standard — nessun verbo nel path

Il metodo HTTP determina l'operazione. Il path identifica solo la risorsa.

```text
GET    /api/v1/{modulo}/{risorsa}/            → lista
POST   /api/v1/{modulo}/{risorsa}/            → crea
GET    /api/v1/{modulo}/{risorsa}/{id}/       → dettaglio
PATCH  /api/v1/{modulo}/{risorsa}/{id}/       → aggiorna
```

|     | Esempio                            | Perche'                                   |
| --- | ---------------------------------- | ----------------------------------------- |
| OK  | `POST /toponomastica/`             | Il metodo POST dice "crea"                |
| NO  | `POST /toponomastica/crea/`        | Il verbo e' nel metodo HTTP, non nel path |
| NO  | `PATCH /toponomastica/5/aggiorna/` | Idem                                      |

### Azioni di dominio — verbo ammesso come ultimo segmento

Operazioni non-CRUD (cambio stato, sospensione, esecuzione pipeline) usano un verbo
breve come ultimo segmento. Il verbo nomina **cosa** e', non descrive *come* si fa.

|     | Esempio                                | Perche'                                         |
| --- | -------------------------------------- | ----------------------------------------------- |
| OK  | `POST /pratiche/3/stato/`              | `stato` e' la sotto-risorsa che cambia          |
| OK  | `POST /pratiche/3/sospendi/`           | Azione atomica, nome diretto                    |
| NO  | `POST /pratiche/3/aggiorna-stato/`     | Descrizione dell'azione, non nome della risorsa |
| NO  | `POST /pratiche/3/esegui-sospensione/` | Descrive l'azione invece di nominarla           |

### Lookup — due pattern, una regola

Per i dropdown/select nel frontend esistono due pattern complementari:

**1. Lookup generico** — per tabelle config con struttura `id, codice, descrizione`:

```text
GET /api/v1/core/lookup/codici/?rel=config.qualifiche
GET /api/v1/core/lookup/codici/?rel=config.stati_pratiche&search=ape
```

Un'unica API, parametro `rel` con whitelist (87 tabelle su 9 schemi, 2026-09-21 — ⚠️ una rel dichiarata qui deve **rispondere**: `config.stati` e `config.titoli_cortesia`, senza `codice`, erano ammesse ed erano un 500; il presidio `test_config_panel_registro_db` attraversa ogni riga del pannello config).
Restituisce sempre `id, codice, codice_interno, descrizione, attivo, codice_stabile`
con paginazione e search. Variante **specializzata** (config `_LOOKUP_SPECIALIZZATE`):
stessa API e contratto + UNA colonna extra per relazione (es.
`pratiche.tipi_prestazione` → `categoria`, `catalogo.unita_misura` → `tipo_uom_id`,
`config.registri_giornale` → `etichetta_key`) — preferirla a un endpoint
dedicato quando serve un solo campo in piu'. ⚠️ Una tabella **senza `attivo`**
si dichiara con `has_attivo: False` (2026-09-19): prima l'handler la
avrebbe rifiutata con un 500, a rel dichiarata ammessa.
Dettagli: `docs/it/backend/core/manual/api_lookup_codici.md`.

**2. Lookup dedicato** — quando servono JOIN o campi extra non riducibili a `id, codice, descrizione`:

```text
GET /api/v1/anagrafiche/province/lookup/     → sigla + regione_descrizione
GET /api/v1/anagrafiche/regioni/lookup/      → stato_descrizione
GET /api/v1/anagrafiche/stati/lookup/        → codice_iso2
GET /api/v1/vendite/famiglie/lookup/         → prefisso_default, lunghezza_default,
                                               gestisce_serie, ammette_regole_fiscali
GET /api/v1/anagrafiche/risorse-umane/lookup/ → display (nome della persona, dalla
                                               vista `vw_risorse_umane_dettaglio`),
                                               qualifica, reparto — `risorse_umane`
                                               non ha codice/descrizione (2026-09-14;
                                               scheda: api_risorse_umane_lookup.md)
GET /api/v1/core/lookup/tipi-entita/          → codice, etichetta_key, key_selector di
                                               `config.tipi_entita` (PK `codice` testo,
                                               niente id/descrizione: il generico non la
                                               serve; 2026-09-19, scheda:
                                               api_tipi_entita_lookup.md)
GET /api/v1/core/lookup/azioni-riga/          → codice_interno, colonna_motivo,
                                               colonna_motivo_chiave di
                                               `config.azioni_riga` (niente `codice`,
                                               due colonne in piu': 2026-10-27,
                                               scheda: api_azioni_riga_lookup.md)
```

⭐ Il lookup **famiglie documento** e' l'esempio di quando un dedicato e'
giustificato: `dbops.fn_get_lookup_codici` torna `id/codice/descrizione/attivo`
e non puo' portare i default della forma del numero ne' le due colonne di
natura, che sono esattamente cio' che il drawer dei registri deve sapere per
precompilare il prefisso e decidere quali campi mostrare.
⛔ **Non e' dietro il cancello dell'amministratore**: lo chiama una schermata di
dominio, e chiuderlo spegnerebbe quei campi per tutti gli altri, in silenzio.

Suffisso `/lookup/` sulla risorsa, senza paginazione.

**3. Parameters** — per valori default e gestione override personali:

```text
GET  /api/v1/core/parameters/defaults/?codes=DEFAULT_IVA_ID,DEFAULT_CURRENCY
GET  /api/v1/core/parameters/settings/
POST /api/v1/core/parameters/settings/override/
DELETE /api/v1/core/parameters/settings/override/{id}/
```

`defaults/` risolve N parametri con override (user → group → emittente → default).
`settings/` lista completa con valori a ogni livello di scope.
`override/` CRUD override personale utente (UPSERT + DELETE).
Vedi: [api_parameter_settings.md](../backend/core/manual/api_parameter_settings.md) per dettagli completi.
Max 20 codici per chiamata su `defaults/`.

**Regola:** usare il lookup generico quando la tabella ha la struttura standard
(`id, codice/codice_interno, descrizione`). Creare un lookup dedicato solo se
servono colonne aggiuntive da JOIN o campi non standard.

| Criterio     | Lookup generico                    | Lookup dedicato                            |
| ------------ | ---------------------------------- | ------------------------------------------ |
| Struttura    | `id, codice, descrizione`          | Campi custom, JOIN                         |
| Endpoint     | `GET /core/lookup/codici/?rel=...` | `GET /{risorsa}/lookup/`                   |
| Paginazione  | Si'                                | No (lista completa)                        |
| Quando usare | Tabelle config standard            | Province, regioni, stati, UO con gerarchia |

#### ⛔ L'ENVELOPE DI UN LOOKUP — `{"results": [...]}`, non la lista nuda

> Un lookup dedicato risponde **`{"data": {"results": [...]}}`**.
> `success_response({"results": ...})`, **mai** `success_response(<lista>)`.

⚠️ **Ed e' un difetto che non da' nessun errore.** I due composable del
frontend — `useLookup` e `useGlobalLookup` — trasformano ogni risposta con
`r.data.data.results` **di default**. Su una lista nuda quella espressione vale
`undefined`: il `ref` delle opzioni passa da `[]` a `undefined`, il primo
`.map()` in un computed solleva, e **Vue svuota il sottoalbero**. A video resta
una schermata bianca, con il backend che ha risposto `200`, nessuna riga nei
log e la suite verde.

⭐ **Successo reale**, 2026-09-08: `GET /api/v1/vendite/famiglie/lookup/`
tornava la lista nuda ed era l'**unica** coppia disallineata in tutto il
progetto (verificate tutte le altre: 17 endpoint `/lookup/` su 20 gia'
conformi). Il drawer dei registri di numerazione si apriva vuoto — in creazione
e in modifica — e l'unica traccia del difetto stava nella console del browser.

**L'eccezione, ed e' dichiarata**: i tre lookup **enum statici** di vendite
(`/vendite/lookup/tipi-variazione-*`, `/ambiti-contratto/`) tornano la lista
nuda per ragioni storiche. ⚠️ Chi li consuma **deve** passare il transform
esplicito — `:transform="(r) => r.data.data"` — e lo fanno, passando tutti da
`TipoVariazioneSelect` e `AmbitoContrattoSelect`.
⛔ Non e' un modello da imitare: un endpoint nuovo usa `{"results": [...]}`, e
cosi' non ha bisogno di nessun transform da ricordarsi.

**Il presidio**: un test che guarda la **forma** della risposta, non solo lo
status — `test_il_lookup_torna_l_envelope_results` in
`apps/vendite/tests/api/test_famiglie_api.py` e' il modello. Uno status `200`
non dice niente su un campo che il frontend legge e non trova.

---

## Architettura a tre layer

Ogni richiesta attraversa tre livelli con responsabilita` distinte:

```text
APIView  (api/views.py)         — parsing, validazione input, envelope risposta
  |
Service  (services/*.py)        — orchestrazione, transazioni, regole Python
  |
Repository  (db/*.py)           — accesso DB via cursor, chiamate a funzioni PG
  |
PostgreSQL                      — stato, vincoli, trigger, funzioni di dominio
```

Nessun livello replica la logica di un altro. Il service non riscrive vincoli gia` nel DB;
la view non contiene logica di business.

### Struttura tipo per app

```text
apps/<dominio>/
  api/
    views_<risorsa>.py  # le view, una famiglia di risorse per file (views.py nelle app piccole)
    urls_v1.py          # le rotte, montate in zeroerp_backend/urls.py sotto /api/v1/<dominio>/
    urls_<risorsa>.py   # (opz.) sotto-urlconf incluse da urls_v1.py — es. vendite: urls_ddt, urls_fatture…
  services/             # Orchestrazione e logica Python
  db/                   # Repository con raw SQL (cursor)
  types.py              # TypedDict per tipizzare le righe DB
  tests/
    api/                # Test endpoint HTTP
    services/           # Test logica service
    db/                 # Test end-to-end sul DB vero (§Test)
```

⚠️ Il nome dell'urlconf non dice la versione: `anagrafiche`, `catalogo`, `config`,
`documenti`, `portale`, `shop` e `ui` montano `urls.py`, le altre `urls_v1.py`, e
**tutte** stanno sotto `/api/v1/` (la sede è `zeroerp_backend/urls.py`, comprese
le rotte condizionali di `ROTTE_CONDIZIONALI`). Fuori da `/api/v1/` ci sono solo
`health`, `/api/schema/` e `/api/docs/` (§Schema OpenAPI).

* App per **dominio** (`vendite`, `anagrafiche`), non per dettaglio tecnico; se uno
  schema DB coincide con un dominio stabile, la cartella dell'app si allinea allo
  schema. Project config in `backend/zeroerp_backend/`.
* Modelli ORM solo dove servono, altrimenti `managed = False`.

### Nomi di repository e service

Un'app può avere più repository e service. Il nome segue il **perimetro semantico**:

| Tipo                       | Nome file                      | Contenuto                                                                                       |
| -------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------- |
| Generico schema            | `<schema>_repository.py`       | List, query, CRUD su entità dello schema senza logica specifica (es. `vendite_repository.py`)   |
| Sottodominio specializzato | `<sottodominio>_repository.py` | Operazioni di un processo autonomo con logica propria (es. `pipeline_repository.py`)            |
| Generico schema            | `<schema>_service.py`          | Facade per operazioni generiche (es. `vendite_service.py`)                                      |
| Sottodominio specializzato | `<sottodominio>_service.py`    | Facade per il sottodominio (es. `pipeline_service.py`)                                          |

* `<schema>` per ciò che non appartiene a un sottodominio: elenchi, ricerche,
  lettura dello stato di un'entità.
* Un file `<sottodominio>_*` **solo** quando il sottodominio ha logica orchestrata
  autonoma (runner, executor, tracing, saga), non per singoli metodi.
* Non si frammenta per entità: tre metodi su `fatture` e due su `lotti` stanno in
  `vendite_repository.py`.
* ⚠️ Un **documento** con il suo ciclo (testata, righe, stati, capability) è un
  sottodominio, non un'entità: in `vendite/db/` ognuno ha il suo repository
  (`ordini_repository.py`, `ddt_repository.py`, `fatture_repository.py`, …), con
  i pezzi comuni nei mixin `_*_repo_mixin.py`.

### Convenzioni del codice Python

* **Header di licenza** sui file nuovi: `templates/python-header.txt`, più un
  breve commento iniziale sullo scopo del file. Lo presidia `scripts/check_license.py`
  (pre-commit), che guarda i file **aggiunti**: il pregresso senza header è un
  debito che cala per decisione, non per attrito.
* Commento `# Scopo: ...` in italiano prima di ogni `def`/`async def`; più
  dettagliato (obiettivo, perimetro, risultato atteso) per chi orchestra
  pipeline, transazioni, dispatch di task o integrazioni esterne. Commenti brevi
  nei blocchi non banali.
* Dopo un `ErrorManager.require(... is not None ...)`, l'`assert`
  corrispondente per il type checker.
* Dopo `row = cursor.fetchone()`, un guard (`if not row`) o
  `assert row is not None` prima di usare `row[...]`.
* Nomi di metodo espliciti e di dominio (`run_pipeline`), mai generici (`run`).
* Errori: helper centralizzato `apps/core/services/error_manager.py`; il mapping
  `codice → HTTP status → ui_action` sta in `apps/core/services/error_policies.py`.
* Niente `try/except Exception` generici nelle view di dominio: `ServiceError`
  nei service e fallback al middleware `apps/core/middleware/api_exception_middleware.py`
  (solo `/api/*`, disattivabile con `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED`).

---

## Base classes per view

Quattro base class in `apps/core/api/base_views.py` eliminano il boilerplate auth/permission:

```python
from apps.core.api.base_views import (
    AdminAPIView,
    DomainAPIView,
    PortaleAPIView,
    ShopAPIView,
)

# Per endpoint di dominio (anagrafiche, vendite, pratiche...)
class ToponomasticaView(DomainAPIView):
    area_funzionale = "anagrafiche"
    is_search_endpoint = True        # opzionale, per throttling ricerca

    def get(self, request): ...      # lista
    def post(self, request): ...     # crea

# Per endpoint riservati ad amministratori (amm-software)
class UtentiListView(AdminAPIView):
    is_search_endpoint = True

    def get(self, request): ...
    def post(self, request): ...

# Per endpoint del portale clienti/fornitori (/api/v1/portale/*)
class PortaleFattureListView(PortaleAPIView):
    def get(self, request): ...

# Per endpoint del negozio online (/api/v1/shop/*, anche pubblici)
class ShopCatalogoView(ShopAPIView):
    def get(self, request): ...
```

| Base class       | Auth          | Permessi                                                                             | Uso                       |
| ---------------- | ------------- | ------------------------------------------------------------------------------------ | ------------------------- |
| `DomainAPIView`  | JWT           | `ZeroERPPermission` + `area_funzionale`                                              | Endpoint di dominio       |
| `AdminAPIView`   | JWT           | `IsAdminZeroERP` (check binding `SUPER_ADMIN`)                                       | Amm. Software             |
| `PortaleAPIView` | JWT           | `PortaleBasePermission` (`ruolo_applicativo ∈ {CLIENTE_PORTALE, FORNITORE_PORTALE}`) | Portale clienti/fornitori |
| `ShopAPIView`    | JWT opzionale | `ShopBasePermission` (anonimo oppure `SHOP_CUSTOMER`)                                | Negozio online            |

### Attributi di classe

| Attributo            | Scopo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Obbligatorio         |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `area_funzionale`    | Schema DB dell'area (es. `"vendite"`, `"anagrafiche"`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Si' su DomainAPIView |
| `is_search_endpoint` | Abilita `SearchBurstRateThrottle`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | No                   |
| `post_permission`    | Codename azione di processo (per comandi specifici)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | No                   |
| `<metodo>_passaggio` | `PassaggioDocumento(testata, documento_kwarg, stato_chiesto=None, campo_stato="stato_codice", risolvi_documento=None, stato_del_modello=None)`, per il **cambio di stato** di un documento portato al modello (guida `modello-documento-di-vendita` §6, M-3): l'azione **non si dichiara**, la catena la legge dalla riga del passaggio (stato corrente → stato chiesto; `None` = il campo `campo_stato` del corpo; `stato_del_modello="emissione"` / `"annullo"` / `"iniziale"` = lo stato di emissione, d'annullo o iniziale letto dal DB a ogni richiesta, per «Emetti», per la rotta di un verbo d'annullo e per «riporta in bozza» del lotto, esclusivo con `stato_chiesto`) con `script.fn_doc_azione_passaggio`, prima della transazione. `risolvi_documento` per una rotta il cui parametro non è l'id del documento (il preventivo ROOT dal `pratica_id`). Con l'azione decide lei (come `post_permission`); senza, il livello sul documento. ⛔ Esclude `<metodo>_permission` sullo stesso metodo; sulla sola classe **nega** (`PASSAGGIO_SENZA_RICHIESTA`). Presidio: `core/tests/test_passaggio_rotte.py` | No |
| `<metodo>_accesso`   | Tipo di accesso (`view`/`add`/`change`/`delete`) che il metodo chiede al livello d'area, quando **non** è quello del suo verbo HTTP. Es. `post_accesso = "view"`: una lettura che viaggia in una POST (la domanda all'assistente AI). Stessa chiave di `<metodo>_permission`. ⛔ Un valore fuori dai quattro **nega** (non ricade sul verbo). Da qui si deriva anche «la chiamata scrive?» (`chiamata_in_scrittura`, catalogo BB) | No |
| `oggetto_permesso_da_richiesta()` | Metodo, per quando l'**oggetto** dipende dalla richiesta (una tabella nel path): torna `(app_label, model_name)` e la catena chiede il livello su quell'oggetto, nell'area di `script.fn_area_di_oggetto`, al posto dell'area della classe; `None` ricade sull'area della classe. ⛔ Valutata sulla **sola classe** (i tool dell'assistente, `valuta_accesso_endpoint`) la richiesta non c'è, e la view **nega** (`OGGETTO_SENZA_RICHIESTA`). Unico uso: il pannello «Gestione tabelle» (`views_config_crud.py`, D-P7 del brief-db-pannello-config-verbo-generico, 2026-09-25) | No |
| `skip_area_check`    | Salta il check area — ammesso solo per endpoint cross-dominio (profilo, sessioni, lookup). ⛔ **Non convive con `area_funzionale`**: la catena lo legge **solo** se l'area non si risolve, quindi una view che dichiara entrambi ha lo skip **muto** e vince l'area in silenzio (trovato il 2026-09-12 su 15 view). ⚠️ E una view con lo skip che **scrive** (`post`/`patch`/`put`/`delete`) senza il `<metodo>_permission` è aperta a chiunque sia autenticato: lecito solo se agisce **su sé stessa**. Presidio: `core/tests/test_skip_area_check_registro.py` | No                   |

`PortaleAPIView` e `ShopAPIView` dichiarano `skip_area_check = True`
implicitamente: il set di endpoint portale/shop e' ristretto e non passa
per la catena livello area. Lo scope dati e' applicato a livello DB via
`scope_policy` + RLS (vedi `docs/it/guide/architettura-multi-face-auth.md`).

### Pattern Dual-Class (ELIMINATO)

Il pattern Base + V1 e' stato eliminato il 15 marzo 2026.
Tutti i moduli usano ora `DomainAPIView`, `AdminAPIView`, `PortaleAPIView`
o `ShopAPIView` direttamente:

```python
class ApiRunLottoPipeline(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "genera_fatture_lotti"

    def post(self, request): ...
```

Non creare classi V1 per nuovi endpoint.

La risoluzione permessi segue la catena: superuser bypass → bypass `SUPER_ADMIN` → azione processo → livello area/oggetto CRUD (dal 2026-10-02 senza il passo «`ruolo_applicativo = DISABILITATO` → nega»: una veste spenta tiene il suo tipo e ha `attivo = false`, quindi non e' l'identita' attiva di nessuna sessione — brief-db-be-fe-area-accessi R-DB-1). Vedi `apps/core/api/permissions.py`.

---

## Endpoint POST (Command API)

### `handle_post_json` — helper obbligatorio

Tutti gli endpoint POST usano `handle_post_json` da `apps.core.api.endpoint_helpers`.
Il helper gestisce in modo centralizzato:

1. Parsing JSON del body (`parse_json_body`)
2. Validazione `Idempotency-Key` (se `require_idempotency_key=True`)
3. Idempotency strong mode (prenotazione con `dbops.fn_idempotency_prenota`: esegui, replay, in corso)
4. Esecuzione handler e wrap in `success_response` — per un'operazione `ATOMICA` in modalità
   forte, insieme all'esito `completed` in una transazione sola (§Idempotency-Key)
5. Gestione errori con `exception_to_error_response`

```python
from apps.core.api.endpoint_helpers import handle_post_json

class ApiPraticaStato(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "cambia_stato_pratica"

    # Scopo: Gestisce la richiesta HTTP POST per cambiare stato pratica.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            pratiche_service.cambia_stato_pratica(
                pratica_id, _V_PRATICA.require_string(payload, "nuovo_stato"),
            )
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)
```

### Validazione parametri

I parametri del payload si estraggono con i validator di `apps.core.api.payload_validators`:

| Funzione                                       | Scopo                                         |
| ---------------------------------------------- | --------------------------------------------- |
| `optional_int(payload, "key")`                 | Estrae int o None, errore se non convertibile |
| `optional_bool(payload, "key", default=False)` | Estrae bool con default: **solo booleani JSON** |
| `optional_iso_date(payload, "key")`            | Estrae `date` da stringa ISO                  |
| `optional_uuid(payload, "key")`                | Estrae UUID                                   |

⛔ **Tre regole del corpo, decise da Tid il 2026-10-20** (brief-be-verifica-documentazione-api):

* **Un flag del corpo è un booleano JSON.** Mai `bool(payload.get("x"))`: `bool("false")`
  è `True` (creava un SUPER_ADMIN e chiudeva un contratto nella successione).
  `optional_bool` delega a `PayloadValidator.optional_bool`: `"false"`, `"1"`, `0` sono
  un 400 col campo. Query string e multipart sono stringhe per natura e hanno i loro
  helper (`qp_bool_optional`), non questo.
* **Una chiave fuori contratto è un 400**, non uno scarto silenzioso:
  `validate_allowed_keys` prima di filtrare il payload, in creazione come in modifica
  (le chiavi gestite a parte — `componenti_overrides`, `richiesta_approvazione` — si
  aggiungono all'insieme ammesso). La risposta «ok» con il valore perso non la vede nessuno.
* **Un campo obbligatorio si legge dal BB** (`PayloadValidator.require_*`), mai con
  `payload["x"]`: una chiave mancante sarebbe un `KeyError`, cioè un 500 per un errore
  di chi chiama.

### Idempotency-Key

| Regola          | Dettaglio                                                                               |
| --------------- | --------------------------------------------------------------------------------------- |
| Header          | `Idempotency-Key` (stringa libera, tipicamente UUID)                                    |
| Obbligatorieta` | **ogni POST che scrive**, per costruzione (`_ApiViewBase.initial`, vedi sotto)          |
| Strong mode     | Attivabile con `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1`, sugli endpoint con `handle_post_json(require_idempotency_key=True)` |
| Prenotazione    | `dbops.fn_idempotency_prenota` (key, utente, endpoint = metodo + percorso, `request_id`, ripresa ammessa), da `IdempotencyStore.claim_or_replay`; registro in `dbops.idempotency_keys` |
| Replay          | Key gia` completata: restituisce risposta cached con header `X-Idempotency-Replayed: 1` |
| In-progress     | Key gia` in elaborazione: `409` con codice `E_IDEMPOTENCY_IN_PROGRESS`                  |
| Key riusata     | Key prenotata da un altro utente o su un altro endpoint: `400` `E_IDEMPOTENCY_KEY_RIUSATA` (la risposta salvata non si rimanda) |
| Key fallita     | `failed`: si riprende sempre, l'operazione si riesegue                                  |
| Key orfana      | `in_progress` oltre `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI`: si riprende solo se l'endpoint è **ATOMICA** |

**L'unità di lavoro** (decisione di Tid del 2026-10-23, brief-be-verifica-documentazione-api
§I.7.2). In modalità forte ogni endpoint dichiara com'è fatta la sua operazione,
`handle_post_json(..., unita_di_lavoro=UnitaDiLavoro.…)`:

| Valore | Com'è fatta | Transazione | Key orfana oltre la soglia |
| --- | --- | --- | --- |
| `ATOMICA` (default) | un'unità di lavoro sola, che **finisce dentro la richiesta** (niente thread, coda o job che continuano tenendo la key) | handler ed esito `completed` in un `transaction.atomic()`; `failed` scritto **fuori**, dopo il rollback | si riprende: se manca l'esito, manca anche l'operazione |
| `A_PASSI` | committa un passo alla volta (pipeline del lotto, numerazione del lotto, push delle commesse) | nessun `atomic` esterno | resta `IN_CORSO` finché scade o il frontend genera una key nuova |

* ⛔ Un endpoint nuovo che lavora a passi **lo dichiara**, e si aggiunge al registro di
  `apps/core/tests/test_unita_di_lavoro.py`; il motivo sta nel commento `⭐ A_PASSI` accanto
  alla chiamata, una sede sola (il presidio è a cricchetto nei due versi).
* ⚠️ L'`atomic` esterno c'è **solo in modalità forte**: senza registro non c'è un esito da tenere
  insieme all'operazione. Un service che compone più scritture resta responsabile del proprio
  `atomic` (§Atomicità).
* ⚠️ **Il diario dentro l'`atomic`.** Dopo un errore DB catturato la transazione è abortita, e una
  riga di `dbops.error_log` scritta lì sparirebbe senza errore: per le ATOMICA
  `ErrorManager.log_error_only` la mette in coda e la scrive a transazione chiusa
  (`ErrorManager.diario_dopo_la_transazione`).
* ⭐ **La soglia sta sopra il timeout di gunicorn** (BE-5). La ripresa è sicura solo perché
  nessuna richiesta vive più del timeout del worker: all'avvio e a ogni `kill -HUP`
  `backend/gunicorn.conf.py` rifiuta di partire, in modalità forte, se
  `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` (chiesta a `dbops.fn_idempotency_soglia_secondi`, la
  stessa lettura della prenotazione: il backend non ricopia la regola) non supera il timeout di
  almeno 30 secondi, se il timeout è 0 (nessun tetto) o se il worker non è `sync`
  (in `gthread` il timeout non è il tetto di una richiesta). Le due impostazioni si cambiano
  insieme.
* Il racconto intero, per chi non legge il codice: la guida
  [Le operazioni che non si ripetono](/guide/operazioni-che-non-si-ripetono).

⛔ **Una POST che scrive porta la key, e lo garantisce la classe base** (decisione
di Tid del 2026-10-20, brief-be-verifica-documentazione-api §A5). Le quattro
porte (`DomainAPIView`, `AdminAPIView`, `PortaleAPIView`, `ShopAPIView`) ereditano
da `_ApiViewBase`, il cui `initial()` — dopo autenticazione e permessi — risponde
**400 `E_IDEMPOTENCY_KEY_REQUIRED`** a ogni POST senza header. Il criterio è la
semantica HTTP: una POST di creazione o di azione non è idempotente. **PATCH, PUT e
DELETE** lo sono, e restano senza obbligo (alcuni endpoint la chiedono ancora con
`handle_post_json(require_idempotency_key=True)`).

- **Una POST che LEGGE lo dichiara**: `post_accesso = "view"` (anteprime, preview dei
  componenti, risoluzione di prezzo e IVA, verifiche). Lo stesso attributo abbassa
  il permesso alla lettura: senza, la POST chiederebbe la key e il livello di scrittura.
- `handle_post_json(require_idempotency_key=True)` resta per la **modalità forte**
  (claim/replay), che il solo controllo di presenza non fa.
- **Frontend**: la key la mette l'interceptor di `core/api.js` (`applicaIdempotencyKey`)
  su ogni POST/PUT/PATCH/DELETE che non ne porta una, una per chiamata. ⛔ Non si
  genera più a mano nelle funzioni API: le 69 copie sono state ritirate.
- **Test**: `ClientApi` (`apps/core/tests/_helpers/jwt_mock.py`, il `client_class` di
  `JwtMockedApiTest`) fa lo stesso. Chi prova l'assenza usa `Client` semplice.
- **Smoke bash**: la funzione `curl()` di `_smoke_https.sh` la mette sulle POST.
- ⚠️ Fino a quel giorno la key era una scelta della singola view: 82 scritture su
  457 la chiedevano, senza un criterio (fatto datato).

---

## Endpoint GET (Read API)

Gli endpoint di lettura restituiscono dati senza modificare lo stato.

```python
class ApiLottiList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True                           # abilita throttling

    # Scopo: Restituisce via GET l'elenco paginato dei lotti fatturazione.
    def get(self, request: Request) -> JsonResponse:
        competenza_mese = optional_iso_date(
            {"competenza_mese": request.query_params.get("competenza_mese")},
            "competenza_mese",
        )
        limit, offset = pagina_da_query(request.query_params)  # la finestra, dal BB
        auth_user_id = get_scope_user_id(request)       # None per superuser

        data = fn_list_lotti(
            competenza_mese=competenza_mese,
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
        )
        return success_response(data)
```

### Query params (filtri lista)

I filtri opzionali da query string si normalizzano con gli helper di
`apps.core.api.payload_validators` (passati **per valore**, es.
`qp_bool_optional(qp.get("attivo"), "attivo")`):

| Funzione                                                            | Scopo                                                                                                   |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `qp_str(raw)`                                                       | stringa o `None` se assente/vuota (strip)                                                               |
| `qp_int_strict(raw, name, default)`                                 | int con default; **400** se presente ma non numerico o fuori da `bigint`                                |
| `qp_int_optional(raw, name, *, min_val, max_val)`                   | int **opzionale strict**: `None` se assente/vuoto, **400** se non numerico o fuori range (default `bigint`) |
| `qp_bool_optional(raw, name, default=None)`                         | il **flag** di query string e multipart: `true`/`false` (maiuscole ammesse), assente/vuoto = `default`, **ogni altro valore 400** |
| `qp_iso_date_optional(raw, name)`                                   | `date` **opzionale strict**: `None` se assente/vuoto, **400** se malformata                             |
| `parse_list_params(qp, *, default_limit, max_limit, default_order)` | bundle `search/limit/offset/order_by/order_dir/page` di una lista                                        |
| `pagina_da_query(qp, *, default_limit, max_limit)`                  | `(limit, offset)` di **ogni** lista: `page`/`page_size` e valori illeggibili sono un **400**, limiti da `limiti_pagina`. Lo usa `parse_list_params` |
| `envelope_da_offset(results, total_count, *, limit, offset)`        | l'envelope paginato (`count`/`page`/`page_size`/`total_pages`/`results`) da una finestra `limit`/`offset`; `page` la ricava `pagina_di(offset, limit)` |

⚠️ **Il tetto di un intero è il tipo DOVE ARRIVA** (dal 2026-10-08): un confronto
`col = %s` regge qualunque intero, un **parametro di funzione** `integer` o un cast
`::integer` no — `3000000000` parte come `bigint`, la funzione non si risolve, e
la risposta è un **500** al posto di un 400. Il default di `qp_int_optional` è
`bigint` (oltre, nessun intero PG); chi passa il valore a un parametro `integer`
dichiara `min_val=INTEGER_MIN, max_val=INTEGER_MAX` (`apps.core.services.payload_helpers`).

**Contratto degli helper `*_optional` (dal 2026-06-04):**

* **valore vuoto** (`?attivo=`) ⇒ trattato come **assente** → `None` (nessun filtro).
  Per omettere un filtro è equivalente non inviare la chiave.
* **valore non riconosciuto / non valido** (`?attivo=banana`, `?utility_id=abc`) ⇒
  **`400` `E_VALIDATION_INPUT`** (niente coercion silenziosa: prima alcuni filtri
  bool accettavano il garbage come `True`/`False`).
* token bool riconosciuti: `1/true/yes/y/on` → `True`, `0/false/no/n/off` → `False`.

#### ⛔ Un filtro a vocabolario chiuso si valida PRIMA della query (dal 2026-10-20)

Un valore sbagliato che arriva nel `WHERE` risponde una lista **vuota** con un 200,
indistinguibile da «non c'è niente». Due forme, secondo chi possiede il vocabolario:

* **una tabella** (`config.stati_doc_*`, `config.tipi_entita`, …):
  `richiedi_codice_a_vocabolario(tabella, colonna, valore, codice_errore=…, parametro=…)`.
  Esistenza e basta: i codici **dismessi** sono ammessi (i documenti vecchi li portano);
* **un CHECK**: una costante specchio + `validate_enum_param`, e la costante si
  iscrive nel registro `core/tests/db/test_specchi_dei_check_db.py`, che la confronta
  col CHECK.

⛔ **Il 400 di un filtro NON porta `field`** (decisione di Tid, 2026-10-20). Un
filtro è un parametro di query, non un input del form in cui l'operatore si trova
(§«Escono solo i nomi»): il valore esce da una select o da un chip, quindi il 400
vuol dire un client che sbaglia (bundle vecchio, URL a mano, client esterno). Il
nome del parametro sta nel messaggio e nel `context` diagnostico, alla chiave
`parametro`. I due BB lo fanno da soli.

Il dettaglio e i consumatori stanno nel catalogo BB backend.

#### ⛔ Un SATELLITE legge prima la sua testata

Una lista o un conteggio «di» un documento (righe, segnalazioni, task-run, contesto)
legge prima la testata nel perimetro, e su un padre inesistente o fuori perimetro
risponde il **404** del dominio, non `200 []` o zeri. Per il lotto c'è il BB
`lotto_visibile` (`vendite/services/_lotto_perimetro.py`); per i documenti
`testata_o_not_found` / `riga_del_padre_o_not_found` — anche sulle **scritture** di
una riga, che va per il solo `riga_id`.

#### ⛔ Un PERIMETRO non è un filtro, e «assente» non vale `False`

Un booleano di lista può essere due cose diverse, e vanno scritte diversamente:

| | Chi decide | «assente» significa | Dove vive il default |
| --- | --- | --- | --- |
| **filtro** (`solo_aperte`) | l'operatore, da un widget | `False` — nessun filtro | nel client, che lo manda |
| **perimetro** (`solo_numerate`) | il **dominio** | **applica la regola** | nel **service/repository**, `= True` |

⭐ *La rata di un documento non numerato non è un credito su cui registrare un
incasso*: è una regola del dominio, quindi vale per **ogni** client — non solo
per quello che si ricorda di mandare il parametro. Un perimetro scritto nel
frontend è una regola di business nella presentazione, e il fatto che oggi il
client sia uno solo non la rende vera.

Forma (decisione di Tid, 2026-09-23, `GET /pagamenti/rate/`):

* la **view** resta sull'helper *strict* (`qp_bool_optional`): `?x=banana` deve
  restare un **400**, non diventare `True` in silenzio. ⭐ Dal 2026-10-20 è
  l'**unico** lettore dei flag di trasporto, col solo vocabolario `true`/`false`
  (Tid, brief-be-verifica-documentazione-api §A6): `qp_bool` (indulgente: tutto
  ciò che non era `0/false/no/n/off` valeva vero), `as_bool` e
  `_parse_optional_bool` (tutto ciò che non era `1/true/yes/on` valeva falso) sono
  ritirati. `1`, `0`, `yes` sono un 400;
* il **service** traduce l'assenza: `True if x is None else bool(x)`, con il
  perché accanto. ⛔ Mai `bool(x)` secco, che mappa `None` su `False`;
* il **repository** dichiara `x: bool = True`, così anche un chiamante interno
  che non ne sa nulla ottiene la regola;
* la **via d'uscita resta e si documenta** (`?x=false`): un perimetro senza
  escape è un dato che manca, non una scelta.

⚠️ **Il sintomo che lo fa emergere sta nel frontend**: un perimetro tenuto in
`filterDefaults` è anche una *chiave di filtro*, quindi il segno dei filtri
attivi lo conta — l'operatore legge «1 filtro attivo» e nel pannello non trova
niente da toccare. *`filterDefaults` risponde a due domande — «cosa mando» e
«cosa conto come filtro» — e per un perimetro le due risposte divergono.*

> **Ordinamento** nel service: `validate_order_params(order_by, order_dir, *, allowed_columns, error_code, function_name, nullable=False)`
> (`apps.core.services.list_helpers`). ⛔ `validate_pagination` (la
> paginazione page-based) è **ritirata** dal 2026-10-21: c'è un dialetto solo.

### Paginazione

| Parametro | Default                | Max                 |
| --------- | ---------------------- | ------------------- |
| `limit`   | `DEFAULT_LIMIT` (25)   | `MAX_LIMIT` (200)   |
| `offset`  | 0                      | —                   |

⛔ **Un dialetto solo: `limit`/`offset`** (decisione di Tid del 2026-10-21).
Ogni lista legge la finestra **solo** da `pagina_da_query` (anche via
`parse_list_params`), che rifiuta `page`/`page_size` con un **400**. La storia:
il 2026-10-20 (brief-be-verifica-documentazione-api §A3) le liste offset-based
smisero di ignorarli in silenzio — chi li mandava riceveva la prima pagina di
25 righe senza errore; il 2026-10-21 anche la ventina di liste che parlava
`page`/`page_size` (dashboard, tracciamento, note, pagamenti, lotti, ricerca
globale, lookup codici, tabelle di configurazione, audit dei permessi) è passata
a `limit`/`offset`, e il frontend non traduce più (`paramsFinestra`).
⛔ Anche `?limit=abc` e `?offset=xyz` sono un **400**: il ripiego muto sul
default (`qp_int`, ritirato) dava la prima pagina a chi ne aveva chiesta
un'altra. ⛔ E così il **fuori limite** (Tid, 2026-10-21): `limit` fuori da
1..tetto della lista è `limit_fuori_limiti_1_<tetto>`, un `offset` negativo è
`offset_negativo`. Fino a quel giorno `limit=500` diventava 200 in silenzio, e
chi chiedeva «tutto» riceveva una parte credendola il tutto. Il clamp di
`limiti_pagina` resta la difesa interna dei repository, non la risposta
all'utente; i service non ripetono il controllo (ritirati quel giorno i guard
di `pipeline_service` e `commesse_service`, irraggiungibili via HTTP). I presidi: `core/tests/api/test_paginazione_dialetto.py` (letture a
mano di `limit`/`offset`, letture di `page`/`page_size`) e, lato frontend,
`src/core/paginazioneDialetto.spec.js` (nessuna chiamata manda
`page`/`page_size`). Nello schema OpenAPI i due parametri li dichiara
`parametri_finestra(default_limit=…, max_limit=…)` (`apps.core.api.openapi_params`).

⭐ **Una sede sola: `apps.core.api.constants`** (2026-09-28). Il default e'
quello che l'operatore vede a video (la misura `PAGINA` del catalogo
`ui.misure_pagina`, che frontend e preset leggono da li'), cosi' una chiamata
senza `limit` risponde come la lista. ⚠️ `DEFAULT_LIMIT` resta un numero del
backend: quanti record chiede al massimo una chiamata e' un tema vicino ma
diverso dalle misure del paginatore (brief-db-misure-pagina-catalogo §6.5). Nei repository il clamp e' il BB `limiti_pagina(limit, offset,
tetto=MAX_LIMIT)`. ⛔ Mai il numero scritto a mano, nemmeno nella descrizione
OpenAPI (`f"... (default {DEFAULT_LIMIT}, max {MAX_LIMIT})"`): lo presidia
`apps/core/tests/test_paginazione_fonte_unica.py`, con le eccezioni dichiarate
(autocomplete, batch). ⭐ Le **liste di eventi** (giornale di una pratica,
registro di una commessa, task run di un lotto) partono da
`DEFAULT_LIMIT_EVENTI` (100), stessa sede. ⛔ **Anche le firme** di service e
repository (dal 2026-10-04): `limit: int = DEFAULT_LIMIT`, mai un numero —
una lista aveva il suo default nella view e un altro, diverso, nella firma; il
presidio le guarda, con le eccezioni (lookup, batch) in `_FIRME_AMMESSE`.

Risposta paginata (l'**envelope** conserva `page`/`page_size`: li ricava
dalla finestra `envelope_da_offset`, e servono al paginatore per leggere dove
il backend ha riportato una pagina stantia):

```json
{
  "data": {
    "count": 142,
    "page": 1,
    "page_size": 50,
    "total_pages": 3,
    "results": [...]
  },
  "meta": { "request_id": "..." }
}
```

Forma ridotta (le liste che non dichiarano la pagina: solo il totale e le righe;
la finestra in ingresso è comunque `limit`/`offset`):

```json
{
  "data": {
    "count": 142,
    "results": [...]
  }
}
```

#### ⛔ Il `count` non si deriva MAI dalle righe che stai consegnando

> Regola scritta il **2026-09-02**, dopo averla vista rotta due volte nello
> stesso giorno e in due forme diverse.

Un endpoint di lista deve calcolare `count` con una **valutazione indipendente**
dalle righe che ritorna:

* **paginato** → `COUNT(*) OVER ()` nella stessa query, tramite il building
  block `fetch_paged_with_total` (`apps/core/db/_helpers.py`), che fa pagina e
  totale in **una** valutazione e ha il fallback per il rientro su una pagina
  stantia. ⭐ Dal 2026-09-28 il ripiego c'e' **sempre**: se il chiamante non
  passa un `fallback_count_sql` suo, il BB rilegge la stessa query con
  `LIMIT 1 OFFSET 0` (serve che finisca con `LIMIT %s OFFSET %s` e abbia
  parametri posizionali, e lo verifica a ogni chiamata). L'offset il BB lo
  legge dall'ultimo parametro della query; `offset=` si passa solo con i
  parametri con nome (dal 2026-10-04: passato e ricavabile, deve coincidere). ⛔ Una `COUNT(*) OVER ()` letta a mano (`extract_paginated`,
  `rows[0][n]`) oltre l'ultima pagina dice totale 0, e la lista a video non sa
  tornare indietro (`useListaEmptyStateFetch` arretra da solo, ma solo su un
  totale vero): si passa dal BB;
* **non paginato** → una `SELECT count(*)` **sua**, con lo **stesso perimetro**
  della lista.

⛔ **`len(results)` non è un conteggio: è un'eco.** Un numero derivato dalle
righe non può dire niente *sulle* righe — vale `rows.length == rows.length`,
sempre vero. Il client che lo usa per verificare di aver ricevuto tutto sta
confrontando una cosa con se stessa.

⚠️ **E la forma sbagliata somiglia moltissimo a quella giusta**: uno dei due
casi del 02-09 era già scritto `{"count": len(atti), "results": atti}`. Leggendolo
sembra a posto — c'è un `count`, c'è un `results`. Non lo è.

**Chi lo consuma e perché conta.** `<ListaConfigurabile>` in modalità
`:paginata="false"` tratta `rows` come il dataset completo: se il backend
paginasse senza dirlo, la lista mostrerebbe un sottoinsieme **senza paginator e
senza errore**. Il building block confronta `rows.length` con `total` e si
rifiuta di disegnare la tabella se divergono — ma quel confronto vale solo se il
`total` è indipendente.

⚠️ **Il perimetro del conteggio deve essere quello della lista, JOIN compresi.**
Con `INNER JOIN` che possono togliere righe, un `count(*)` sulla sola tabella
madre conta di più di quanto la lista consegna e fa scattare il guard su un
troncamento che non esiste. ⇒ Si condivide il frammento `FROM`+`WHERE` fra le
due query, non lo si riscrive.

#### ⭐ `parse_list_params`: `order_dir` assente è `None`, e decide il repository

Dal **2026-09-26** `parse_list_params(qp)` restituisce `order_dir = None` quando
il client non lo manda (o lo manda vuoto), e il valore ripulito dagli spazi
quando c'è. **Non lo valida**: la direzione estranea la rifiuta chi ordina, con
la regola unica `order_dir_ammessa` — il service (`validate_order_params`,
`PayloadValidator.validate_order_by`) col codice del dominio, o il BB SQL
(`sql_order_direction`) col 400 `E_VALIDATION_INPUT`.

🔴 **Fino a quel giorno l'assenza diventava `"asc"`**, e il difetto era muto: il
`default_desc` e le `colonne_desc` dei repository si accendono solo su `None`,
quindi una lista che deve aprirsi dal più grave (o dal più recente) si apriva al
contrario, senza errore. Il ripiego che questa sezione prescriveva — passare
`qp_str(qp.get("order_dir"))` invece di `p["order_dir"]` — è stato **ritirato**
dalle view che lo usavano solo per la direzione.

⭐ **Le date partono DESC anche dal nome, e il default segue la lista** (dal
2026-10-20, Tid). `parse_list_params(default_order=...)` riempie `order_by` con la
colonna di default: fino a quel giorno `sql_order_clause` la trattava come una
colonna scelta e ignorava `default_desc`, e ordini, resi, DDT, fatture, contratti e
preventivi si aprivano dal più vecchio. Ora la colonna di default segue
`default_desc` (una coda si apre crescente apposta, come le rate), e ogni altra
colonna data chiesta senza verso parte DESC, dichiarata in `colonne_desc` **o
riconosciuta dal nome** (`e_chiave_data`: `data`, `data_*`, `*_at`, `*_dal`/`*_al`,
`competenza_mese`). Chi compone l'`ORDER BY` a mano passa
`sql_order_direction(order_dir, default_desc=e_chiave_data(order_by))`.

⚠️ **Un validatore di dominio che riceve `p["order_dir"]` deve ammettere
l'assenza**: `validate_order_params(..., nullable=True)`. Senza, la lista
risponde 400 a una richiesta senza verso (era il caso dei quattro validatori di
catalogo e listini, allineati lo stesso giorno).

⚠️ **`order_by` è un'altra storia, e resta**: il bundle ha un `default_order`
(`"descrizione"` se non lo si passa) che per molte liste non è una colonna. Lì
`order_by` si legge ancora grezzo (`qp_str(qp.get("order_by"))`), per quel
motivo e non per la direzione.

#### ⛔ Un `order_by` fuori whitelist è un 400, in ogni lista (dal 2026-10-20)

Decisione di Tid (brief-be-verifica-documentazione-api §A1). Una chiave di
ordinamento **indicata** e assente dalla whitelist della lista risponde **400
`E_VALIDATION_INPUT`** (`order_by_invalid`), o il 400 del dominio dove il service
la valida prima. Una chiave **non indicata** prende il default della lista.

Fino a quel giorno metà delle liste (anagrafiche, vendite, amm-software…)
ripiegava in silenzio sul default: rispondeva 200, ordinata diversamente da come
era stato chiesto, e nessuno lo vedeva. La sede della regola è il BB
`colonna_ordinamento` (catalogo BB §Ordinamento SQL), letto da `sql_order_clause`,
da `sql_order_direction_lista` e dai repository che compongono l'`ORDER BY` a mano.
⛔ Mai più `COLS.get(order_by, default)`.

⚠️ Il `default_order` di `parse_list_params` arriva al repository come se il client
l'avesse chiesto: dev'essere una **chiave della whitelist**, o `""` per lasciare il
default al repository.

#### La whitelist di ordinamento si chiava sul `campo_sorgente` FISICO

`<ListaConfigurabile>` monta le Column con `:field="col.campo_sorgente"`, quindi
`order_by` porta il nome **fisico** del catalogo, non il codice logico.

⚠️ E il **valore** della whitelist è la colonna per cui si ordina davvero:
**si ordina la colonna che si vede**. Una chiave `centro_descrizione` mappata su
`centro_codice` ordina per un campo che a video non c'è, e se i due non sono
correlati l'ordine sembra arbitrario a chi guarda (corretto il 2026-09-02).

⚠️ Se la colonna è un'espressione della `SELECT` (un `CASE`, una sottrazione),
si ordina per il suo **alias** — PostgreSQL lo ammette in `ORDER BY` — e non
riscrivendo l'espressione: una copia riscritta può divergere dall'originale, e
la lista si ordinerebbe diversamente da come si legge.

⭐ **E la frase nello schema OpenAPI si LEGGE dalla whitelist**, non si ricopia
accanto a lei: `descrizione_order_by(SORT_COLUMNS, nota)` di
`apps/core/api/openapi_params.py` (2026-09-18). Un elenco scritto a mano nella
`description` di `order_by` è già divergente il giorno in cui la mappa prende
una colonna — ed era successo due volte in pagamenti prima del BB.

### Ricerca e throttling

* `is_search_endpoint = True` sulla view abilita `SearchBurstRateThrottle`
* Ricerca testuale: parametro `search`, operatore ILIKE. ⭐ Sulle liste
  configurabili la **soglia è della lista** (dal 2026-09-26): la dichiara il
  catalogo (`ui.lista_definizione.ricerca_min_caratteri` — 1 sulle tabelle di
  configurazione a codici corti, 3 sulle altre), il BB
  `add_ricerca_full_condition` la legge da lì e sotto soglia il termine non
  filtra; la stessa colonna arriva al frontend nella configurazione della lista
  (chiave `ricerca_min_caratteri`). ⛔ Nessun repository e nessuna view la
  scrivono a mano, e **nessuna lista a catalogo risponde 400** sotto soglia: il
  termine corto semplicemente non filtra (decisione di Tid del 2026-09-26). Le
  ricerche che non sono una lista a catalogo (ricerca universale, lookup)
  restano alla soglia di progetto `RICERCA_MIN_CARATTERI` (3), col 400
  `E_SEARCH_VALIDATION` di `require_min_search_length`
* Vedi: `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md`

### ⭐ Capability di riga — come viaggia il motivo di un'azione spenta

> **La regola non nasce qui**, e questa sezione non la riscrive: sta in
> [linee-guida-sql §12](/linee-guida-sql) per chi la produce e in
> [frontend-standards](frontend/frontend-standards.md) per chi la rende. Qui c'è
> la faccia che mancava — **il trasporto** — perché una regola scritta su due lati
> di tre si perde nel mezzo, ed è successo davvero: il pulsante «Annulla
> l'accredito» e il cestino del mapping billing account erano **accesi** su gesti
> che il database avrebbe rifiutato.

**Permesso ⇒ nascondi. Stato ⇒ disabilita col motivo.** Ne discende che la
risposta deve portare **due cose**, non una: se dice solo *«non si può»*, il
client ha un pulsante grigio che non spiega niente — indistinguibile da un bug.

| Ruolo del campo | Tipo           | Cosa porta                                              |
| --------------- | -------------- | ------------------------------------------------------- |
| il flag         | bool           | `false` = azione **da disabilitare**, non da nascondere |
| il motivo       | string \| null | codice **macchina** del primo motivo. `null` = ammesso  |
| la chiave       | string \| null | **chiave i18n** del tooltip                             |

⚠️ **Sui NOMI non c'è ancora una forma unica, e questa tabella non ne inventa
una.** Le famiglie in servizio sono tre, e nessuna è il calco delle altre:

| Superficie                                           | Flag                | Motivo                                    | Chiave i18n                                                                                  |
| ---------------------------------------------------- | ------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------- |
| dettaglio documento                                  | `can_push_commessa` | `can_push_commessa_reason`                | `can_push_commessa_reason_key`                                                               |
| riga `sveglie[]` del dettaglio processo (2026-09-15) | `can_esegui_ora`    | `can_esegui_ora_reason`                   | `can_esegui_ora_reason_key` (+ `can_esegui_ora_dettaglio`, i parametri con nome della frase) |
| riga mapping BA                                      | `can_remove`        | `rimozione_blocco_reason`                 | `rimozione_blocco_reason_key`                                                                |
| righe reso · coda accrediti                          | —                   | `annullo_blocco_codice` · `blocco_codice` | —                                                                                            |
| riga del piano d'inventario (magazzino, 2026-09-23)  | — (`esito = NON_POSTABILE`) | `posting_blocco_reason`         | `posting_blocco_reason_key`                                                                  |
| dettaglio operatore (amm. software, 2026-09-27)      | `can_invite` · `can_disable` · `can_demote_super_admin` · `can_set_valido_al` (2026-10-07) | `invite_reason` · `disable_reason` · `demote_reason` · `valido_al_reason` | `invite_reason_key` · `disable_reason_key` · `demote_reason_key` · `valido_al_reason_key` |

⭐ **Solo le prime due sono terne coerenti** (la famiglia 1): motivo e chiave
si ricavano dal nome del flag, quindi chi ne legge uno sa già come si chiamano
gli altri due — e il client le legge con un solo prefisso
(`bloccoAttivo(riga, 'can_esegui_ora', 'can_esegui_ora')`). La terza ha il
motivo che non discende dal flag; la quarta non ha flag **e** porta due nomi
diversi per la stessa cosa su due superfici. La quinta, il piano d'inventario,
non ha flag perché l'esito della riga lo è già, e porta la coppia col nome del
verbo che blocca (`posting_`). La sesta, il dettaglio operatore, ha il flag col verbo (`can_invite`) e la coppia col solo verbo (`invite_reason`, `invite_reason_key`): il motivo non discende dal flag, come nella terza, ma motivo e chiave sì fra loro — il client le legge con `bloccoMotivo` e il prefisso del verbo (`motivoBloccoRiga(t, te, dettaglio, 'invite')`). E la terna `can_registra` · `can_registra_reason`
· `can_registra_reason_key` del documento interno di magazzino è della famiglia 1. ⚠️ Il predicato di «Esegui ora»
sta in **Python** (`avvio_manuale.motivi_esegui_ora`) perché la whitelist è del
deploy e il database non conosce le unit — ma la regola del trasporto vale
uguale: lo stesso predicato serve capability, endpoint e handler.

⇒ Ciò che **vale in tutte** è la proprietà, non il template: il nome dice
**quale verbo** blocca, e motivo e chiave viaggiano **in coppia**. Un
`blocco_reason` generico su una riga che ha due azioni bloccabili le confonde al
primo che si aggiunge (`linee-guida-sql §12.5.4`).

⛔ **Unificare i nomi è una decisione che nessuno ha preso**, e non va presa di
straforo rinominando: finché non c'è, si segue la famiglia della superficie su
cui si sta lavorando invece di coniarne una quarta.

⛔ **Il testo del motivo non viaggia mai nel payload.** Va la chiave: il
messaggio è multilingua e vive nei `locales`, e una frase composta in SQL
sarebbe una traduzione che nessuno può cambiare. ⚠️ Il client usa la chiave con
un ripiego sul codice (`labelOrCode`): chiave mancante ⇒ si vede il codice
macchina, non un tooltip vuoto.

⛔ **Il backend TRASPORTA, non deduce.** Il flag si deriva dal motivo
(`reason is None`), e il motivo lo produce la **stessa** funzione che il
database usa per rifiutare — `script.fn_check_<azione>`, chiamata sia dalla
madre che solleva l'errore sia dalla query di lista. Così tooltip e rifiuto non
«coincidono oggi»: **non possono divergere**. Ricalcolare la condizione in
Python è la forma in cui i due si sfilano in silenzio.

⚠️ **E l'errore resta**, non viene sostituito: la capability è cosa si *propone*,
il guard è cosa si *ammette*. Un client che non legge la capability prende il
409 e ha ragione lui.

**Due forme, e non sono intercambiabili:**

|          | Azione di **documento**                      | Azione **per riga**                                              |
| -------- | -------------------------------------------- | ---------------------------------------------------------------- |
| dove sta | blob `capabilities` nel **dettaglio**        | **colonne della riga** di lista                                  |
| esempio  | `fn_available_actions_preventivo`            | `can_remove` + `rimozione_blocco_reason` su `…/billing-account/` |

⛔ Una capability di dettaglio **non** risponde per una riga: il blob non sa
niente delle righe. È l'errore in cui si cade per primo, perché la forma di
dettaglio è quella già scritta.

⚠️ **Il nome del campo dice QUALE verbo**, e non si riusa quello di un altro:
su una riga possono esistere due azioni bloccabili per motivi diversi, e un
`blocco_reason` generico le confonde al primo che si aggiunge.

⭐ **Prima di dichiarare fatta una capability, verificare che il client la
LEGGA.** Un campo dichiarato e mai letto sembra presidiato e non presidia niente:
nel 2026 il motivo di un pulsante spento non era **mai** stato reso a video,
perché il frontend leggeva un nome di campo diverso da quello emesso — e niente
falliva.
⭐ Dal 2026-09-23 c'è anche un cancello, e legge il contratto dalla sorgente
giusta: `npm run guard:capability` (`frontend/scripts/check-capability-contratto.mjs`)
confronta ogni campo letto da un blob `capabilities.*` con le chiavi che le
`script.fn_available_actions_*` (e `fn_capability_promo_articolo`) emettono,
prese dalla **doc auto-generata** — anche i nomi passati al BB
(`flag('can_x')`, `editFlag`).
⭐ Dalla conversione alla forma annidata (sotto) **conta anche le letture
piatte**: una chiave di primo livello del blob letta fuori da `capabilities`
è rossa, salvo gli omonimi dichiarati col motivo in
`frontend/scripts/capability-letture-piatte.json` — un registro che può solo
calare.

### ⛔ Il blob sta SOTTO `capabilities`, non fuso nel dettaglio

> **Decisione di Tid, 2026-09-23.** Una capability di documento viaggia in una
> chiave sua — `detail.capabilities.can_x` — e **non** si fonde nel dettaglio.

**Perché, sul modello.** Il dettaglio dice **com'è fatto** il documento; la
capability dice **che cosa ci si può fare adesso**. Sono due cose con due
autori: la prima la scrivono le colonne, la seconda una funzione che legge lo
stato e i guard. Fonderle in un dizionario solo perde quell'origine, e con essa
la possibilità di dire chi ha scritto cosa.

Tre conseguenze, ed è da queste che si riconosce il difetto:

* ⛔ **il merge nasconde le collisioni**: il giorno in cui una testata avrà una
  colonna che si chiama come un campo del blob, uno dei due vince **in
  silenzio** — nessun errore, nessun lint, un valore diverso da quello che
  qualcuno credeva di leggere;
* ⛔ **il piatto invita a scriverci dentro**, e succede già: un service
  *arricchisce* il blob in Python prima di fonderlo, sovrascrivendo campi che
  il database aveva deciso. A quel punto «il backend trasporta, non deduce» è
  già infranto, e non l'ha deciso nessuno: l'ha reso facile la forma;
* ⛔ **il piatto non è presidiabile**: `detail.can_x` è indistinguibile da un
  campo del dettaglio, quindi nessuna analisi statica può dire se quel nome è
  un campo che il database emette davvero o un refuso.

⚠️ **Non è una preferenza di stile ed è nata da un'asimmetria vera**: al
2026-09-23 convivevano le due forme — commesse e magazzino annidate; DDT,
resi, ordini, contratti, promo articoli, offerte, preventivi e lotto piatti —
e **nessun documento diceva quale fosse quella giusta**. È la ragione per cui questa sezione esiste: una
regola che non sta scritta non è una regola, e la divergenza non era colpa di
chi l'ha scritta in un modo o nell'altro.

✅ **Il frontend legge da un posto solo**: `useEntityCapabilities` è il BB che
unifica la lettura; motivi, chiavi i18n e sotto-oggetti (`pdf`) si leggono dal
suo `capabilities`, mai da `detail.x`.
✅ **Il pregresso è convertito** (2026-09-23, tutti i dettagli in un giro, senza
doppia lettura):
[brief-be-fe-capability-annidata.md](work-done/brief-be-fe-capability-annidata.md).

⚠️ **La chiave c'è sempre**: un dettaglio che ripiega quando la capability
fallisce (offerte, lotto) consegna `capabilities: {}`, non la omette — la
forma non dipende dall'esito, e il client cade spento (fail-closed).

⛔ **Si trasporta tutto il blob, sotto-oggetti compresi.** Il blob ha chiavi di
primo livello che non sembrano capability — `pdf` (`{mode, allow_allegati}`),
`stato_info_key`, `stato_temporale`, `min_valido_*` — e sono quelle che una
conversione dimentica: il 2026-09-23 i drawer passavano `detail.pdf` al
pulsante PDF, e annidato il blob il pulsante avrebbe perso il `mode` senza
nessun errore. Le chiavi di primo livello si leggono dal
`RETURN jsonb_build_object(...)` della funzione nella doc auto-generata.

---

## Endpoint PATCH (aggiornamento parziale)

Usato quando un'entita` ammette modifica di campi specifici senza che questo costituisca un'azione di dominio distinta (es. aggiornare descrizione o scadenza di una pratica).

⛔ **Una PATCH senza campi è un 400, in ogni dominio** (decisione di Tid del
2026-10-20, brief-be-verifica-documentazione-api §A2). Il service la rifiuta col
BB `PayloadValidator.require_campi_da_aggiornare` sui campi **già estratti** (dopo
whitelist e normalizzazione), prima di scrivere. Fino a quel giorno lo stesso
corpo `{}` rispondeva in tre modi: 400 in alcuni domini, **404 su un record che
esiste** in anagrafiche (l'UPDATE vuoto tocca zero righe), **200 senza scrivere**
altrove — un «salvato» che non ha salvato. Presidio trasversale:
`apps/core/tests/test_patch_vuota_e_400.py`.

⭐ **In PATCH una chiave presente si scrive, anche `null`; una chiave assente non
si tocca.** `null` su un campo nullable lo svuota; su un campo NOT NULL (un flag,
una descrizione obbligatoria) è un 400, mai un «spegni» o un «lascia com'è».
⛔ Niente `dynamic_update` (None = «non toccare») per una PATCH che riceve il
`null` dal client: è il difetto che rendeva impossibile svuotare un campo in geo
(2026-10-20). La lettura per presenza ha un BB, **`PayloadValidator.campi_per_presenza`**
(testi nullable/NOT NULL con `max_len`, maiuscoli, id nullable/obbligatori, flag
NOT NULL, lettori di dominio per le altre forme; chiave fuori contratto e PATCH
vuota sono 400 dentro il BB): non si riscrive a mano.

### Quando usare `handle_post_json` vs `request.data`

| Metodo | Protocollo | Motivo |
| --- | --- | --- |
| **POST** (create, azioni) | `handle_post_json` | Corpo come oggetto, idempotency (presenza della key e modalità forte), envelope uniforme |
| **PATCH/PUT/DELETE** che chiedono la **modalità forte** | `handle_post_json(require_idempotency_key=True)` | Gesti da non ripetere: cancellazione di un fondo, di una riga di distinta, di una credenziale; le preferenze lista e dashboard |
| **PATCH/PUT** (update, replace), tutte le altre | `corpo_oggetto(request)` | Una riga, nessun wrapper: errori dal service e dal middleware |

⭐ **Una regola, un modo** (Tid, 2026-10-25). Il criterio non è il verbo ma il bisogno di
modalità forte. Fino a quel giorno le PATCH/PUT avevano due dialetti, `corpo_oggetto` e
`handle_post_json`/`handle_detail_patch` (16 view, nessuna con la modalità forte). Davano lo
stesso risultato, perché tutti e due leggono `request.data` e applicano `oggetto_json`
(E-6, 2026-10-07). Le 16 view sono passate a `corpo_oggetto` e `handle_detail_patch` è
ritirato. ⚠️ Il motivo scritto prima qui («`handle_post_json` fa `json.loads()` su un corpo
già consumato da DRF») non valeva più: per una richiesta DRF `parse_json_body` legge
`request.data`. Presidio: `core/tests/api/test_corpo_oggetto.py`
(`DialettoPatchPutTests`), che legge il codice e segnala ogni `patch`/`put` che
chiama `handle_post_json` senza `require_idempotency_key=True`.

Esempio PATCH corretto (pattern adottato):

```python
class OperatoriDetailView(AdminAPIView):
    def patch(self, request, auth_user_id):
        result = AmmSoftwareService().update_operatore(auth_user_id, corpo_oggetto(request))
        return success_response(result)
```

⛔ **Mai `request.data` grezzo** (F-9, 2026-09-27). Il JSON valido non è per
forza un oggetto: con una lista `request.data` è quella lista, il primo
`.get()` è un **500** e `dict(request.data)` su una lista di coppie la
trasforma in un oggetto **in silenzio**. `corpo_oggetto` (in
`payload_validators`) applica la stessa regola di `handle_post_json`
(`oggetto_json`) e risponde 400 `E_VALIDATION_INPUT` nell'envelope, anche per
il JSON illeggibile. Non si ripiega su `{}`: eseguirebbe la richiesta coi
default.

La view resta sottile (una riga). L'error handling e' garantito dal service
(`ServiceError`) e dal middleware (`ApiExceptionMiddleware`), non serve il
wrapper `handle_post_json` (salvo la modalità forte, seconda riga della tabella sopra).

---

## Envelope risposte

### Successo

```json
{
  "data": { ... },
  "meta": { "request_id": "uuid-..." }
}
```

Generato da `success_response()` in `apps.core.api.success_responses`.

### Errore

```json
{
  "error": {
    "code": "E_PIPELINE_VALIDATION",
    "message": "Tipo documento fiscale non valido.",
    "detail": "tipo_doc_fiscale_id=42 non trovato",
    "retryable": false,
    "ui_action": "highlight_form_fields",
    "fields": ["tipo_doc_fiscale_id"],
    "targets": [{ "type": "FATTURA", "id": "820" }]
  },
  "meta": { "request_id": "uuid-..." }
}
```

| Campo               | Sempre presente | Note                                                                                                                                                   |
| ------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `code`              | si`             | Codice errore strutturato (es. `E_PRATICA_NOT_FOUND`)                                                                                                  |
| `message`           | si`             | Messaggio business-safe, visibile all'utente finale                                                                                                    |
| `detail`            | no              | Dettaglio tecnico aggiuntivo                                                                                                                           |
| `technical_message` | no              | Solo se `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1` (mai in produzione)                                                                                    |
| `retryable`         | no              | `true` se il client puo` riprovare la stessa richiesta                                                                                                 |
| `ui_action`         | si`             | Come dovrebbe reagire la pagina. ⚠️ **Ramificato su un valore su sette**; gli altri sei li serve il default, e dal 2026-09-09 è dichiarato — vedi sotto |
| `fields`            | no              | I **nomi** dei campi del form da correggere (`["partita_iva"]`)                                                                                        |
| `targets`           | no              | **Su quale cosa**: `[{type, id}]`, al massimo cinque                                                                                                   |
| `hint`              | no              | L'**azione suggerita**: cosa può fare l'operatore adesso. ✅ Reso a video dal 2026-09-09, sotto il messaggio                                            |

⭐ **`fields` — dal 2026-08-08.** È l'informazione senza la quale
`ui_action: highlight_form_fields` non è azionabile: diceva *«evidenzia il
campo»* senza dire quale. Arriva dal `context` del `ServiceError`, dalla
convenzione `context={"field": <nome>}` già presente in **114 punti di
chiamata** — non è una convenzione nuova, è una che si fermava al log.

⭐ **`hint` — dal 2026-08-18.** È la `soluzione` che il team DB scrive **a
catalogo per ogni codice** (*«se il documento non è ancora numerato, la strada è
il reset del lotto…»*): la parte che dice all'operatore cosa fare. PostgreSQL la
consegna come `HINT` dell'eccezione.

🔴 **Prima non arrivava, ed è il motivo per cui la modifica esiste.**
`ErrorTranslator._from_database_error` la leggeva già dalla diag psycopg — ma
quel ramo vale solo per un `DatabaseError` che arriva **nudo** al middleware, e
appena un service traduce con `translate_db_errors` (cioè sempre, in ogni
dominio) non ci passa: il `ServiceError` nasceva **senza `hint`** e la frase
restava annegata nel testo grezzo di `detail`.

Ne discendeva che un dominio che volesse mostrarla doveva **riscriverla in
Python**, cioè duplicare il catalogo. Ora il campo viaggia strutturato fino
all'envelope.

✅ **E dal 2026-09-09 il frontend lo LEGGE e lo mostra.** Fino a quella data la
riga qui sopra diceva *«il frontend non lo legge ancora — zero occorrenze in
`frontend/src`»*, ed era vera: il database la scriveva, il backend la
trasportava con cinque punti di traduzione allineati e un BB dedicato, e lo
schermo la buttava. ⭐ **Non è stata corretta la frase: è stato corretto il
codice** — è la stessa mossa già usata per lo stack, e la regola è che *un
documento che dice il vero su un difetto non si aggiorna, si rende falso
chiudendolo*.

Il consumatore è **uno solo**, ed è la sede giusta: `useApiHandler` lo estrae
(`soluzione`) e lo consegna al toast, che lo rende **sotto il messaggio** — nel
`detail` di PrimeVue, non concatenato al testo. ⚠️ Come per il gesto, non c'è
niente da scrivere nei componenti: i file che usano `execute` ce l'hanno senza
una riga di modifica.

⛔ **Su un codice tecnico il suggerimento NON esce**, ed è la condizione perché
il campo sia mostrabile. `_apply_policy` lo toglie sui **tre** codici di
`is_technical_code` — `E_DATABASE`, `E_PIPELINE`, `E_GENERICO` — perché lì il
canale `HINT` non porta la soluzione di nessun catalogo: porta ciò che
PostgreSQL scrive per lo **sviluppatore**, in inglese (*«Perhaps you meant to
reference the column …»*). Sono gli stessi tre in cui `message` è già sostituito
dalla policy e `detail` da `_sanitize_public_detail`: *il suggerimento
accompagna il messaggio, e dove il messaggio non è più quello dell'errore il
suggerimento accompagnerebbe un'altra frase.*

⚠️ **E la regola NON è quella del bersaglio**, che guarda **anche** lo status. Su
un codice di classe `TECNICO` **registrato a catalogo** il bersaglio non esce e
la soluzione sì: su un 500 non c'è nessun gesto da offrire, ma «segnalare al
supporto citando il request_id» è esattamente ciò che chi legge può fare. Due
campi, due regole, e la differenza è scritta nei test
(`test_error_translator_soluzione.py`, casi 5 e 6).

⚠️ **Escono solo i nomi, e solo dalla chiave `field`.** Il `context` è una borsa
diagnostica destinata a `dbops.error_log`: contiene anche `lotto_id`,
`contratto_id`, `order_dir`, che non sono campi di un form — mandarli direbbe al
client di evidenziare cose che sullo schermo non esistono. E il **valore** non
esce mai: è il dato che l'operatore ha appena scritto.

⭐ **La promessa e il canale sono presidiati insieme (dal 2026-09-21).**
`ui_action = highlight_form_fields` è una promessa, `fields` è ciò che la
mantiene, e i due viaggiano su binari diversi: un override che promette il
campo con nessun punto di sollevamento che lo manda è un toast senza input
rosso, e non fallisce niente. `apps/core/tests/test_ui_action_e_canale_campi.py`
(presidio C2, opt-in `ZEROERP_TEST_DB_E2E=1`) incrocia il catalogo BE con i
siti Python (AST) e con `dbops.vw_punti_canale_campo` per i siti PL/pgSQL:
ogni codice `highlight_form_fields` deve avere **almeno un** sito che
valorizza il canale (`context={"field": …}`/`fields=` in Python, `'campo'` o
`'parametro'` nel context di `fn_log_and_raise_error`), salvo esenzione con la
ragione nel test. ⚠️ Vale anche il verso opposto: `highlight_form_fields`
promette un input **nella pagina in cui l'operatore si trova** — un id
dall'URL, una query string, un header, un parametro di firma **non** lo sono,
e lì la promessa è sbagliata, non il canale: l'override esce. Brief:
`work-done/brief-be-presidio-ui-action-e-canale-campi.md`.

⭐ **`targets` — dal 2026-08-24.** È l'**altra metà** di `fields`, e la
differenza vale la riga: `fields` dice quale campo correggere **dentro la
pagina in cui l'operatore già si trova**; `targets` dice a quale **altra cosa**
deve andare. Il primo evidenzia un input, il secondo fa disegnare un **gesto** —
*«Apri la fattura 820»*.

Forma: un array di `{type, id}`, al massimo cinque. `type` è un codice di
`config.tipi_entita` (`FATTURA`, `COMMESSA`, `LOTTO`…), **mai** un nome di
tabella — il catalogo dei messaggi serve anche il portale cliente e lo shop, e
lì i nomi delle tabelle sarebbero ricognizione regalata.

⚠️ **È un'offerta, non una promessa.** Il bersaglio può puntare a qualcosa che
chi legge non può aprire (permessi, perimetro emittente, record cancellato): il
messaggio si mostra lo stesso, **il pulsante non compare**. Mai un pulsante che
porta in un vicolo cieco.

⛔ **Mai su un codice `TECNICO`.** Su un 500 l'operatore non ha niente da fare,
quindi non c'è nessun gesto da offrirgli: `_apply_policy` lo toglie, anche se il
database ce l'avesse messo.

Brief: `docs/it/dev/work-done/brief-db-bersaglio-errore.md` (§2, §4.4, §7-bis).

### 🔴 I cinque punti di traduzione, e perché contano

Un errore sollevato da `script.fn_log_and_raise_error` porta tutto: codice,
campo, bersaglio, causa, soluzione. **Poi qualcuno lo traduce in `ServiceError`,
e la traduzione decide cosa sopravvive.** Misurato il 2026-08-24: i punti sono
**cinque** (più un sesto appiattimento che non produce un envelope), e **quattro
su cinque** buttavano via la diagnostica strutturata.

|     | Dove                                                                               | Prima del 2026-08-24                |
| --- | ---------------------------------------------------------------------------------- | ----------------------------------- |
| 1   | `ErrorTranslator._from_database_error` — il `DatabaseError` **nudo** al middleware | `hint` + `fields` ✅                 |
| 2   | `payload_helpers.translate_db_errors` — **46** punti di chiamata                   | il solo `hint`                      |
| 3   | `ErrorManager.raise_from_database_error` — **9** punti                             | niente                              |
| 4   | `pipeline_step_executor._run_per_fattura_task`                                     | il solo `message_primary`           |
| 5   | `pratiche._raise_known_db_error` — **12** punti                                    | il solo `hint`                      |
| —   | `pipeline_runner._drive_lotto_until_done` → `errore` del payload                   | ⚠️ **non è un envelope**: vedi sotto |

⚠️ **Il quinto è stato trovato DOPO gli altri quattro**, col roll-out del
2026-08-24 — ed è la ragione per cui questo elenco va riletto invece che dato
per completo: **un BB unifica la lettura, non il trasporto.**

⭐ **Ne discendeva un difetto già vivo, non del bersaglio**: il canale `COLUMN`
viaggia dall'08/08 ed è valorizzato da quasi tutti i punti di sollevamento — ma
`fields` arrivava all'envelope **solo dal punto 1**, cioè quasi mai. I 136
binding di `campiErrati` sul frontend non si illuminavano su nessun errore nato
in PL/pgSQL.

➡️ **La lettura ora è UNA**, il BB `diagnostica_db(exc)` in
`apps/core/services/db_error_fields.py`: ritorna codice, messaggio, causa,
soluzione, campo e bersagli in un colpo solo. I cinque punti la usano, e
`ServiceError` porta `fields` e `targets` fino all'envelope.
⚠️ **Il BB unifica la lettura, non il trasporto**: che il valore arrivi
all'envelope resta scritto in ciascun punto — ed è presidiato da
`apps/core/tests/services/test_db_error_target.py`, che ha **un test per punto**.

### ⚠️ Il runner risponde 200 anche quando fallisce

Gli endpoint di pipeline (`run_lotto_pipeline_until_done`, `numera_lotto`)
rispondono **200 anche quando la catena si ferma per errore**: il fallimento è
un campo del payload — `motivo_stop` più `errore` — perché la catena può aver
eseguito qualche step prima di fermarsi e quel lavoro va raccontato.

```json
{ "data": { "motivo_stop": "ERRORE",
            "errore": { "code": "...", "message": "...", "detail": "...",
                        "hint": "...", "fields": [...], "targets": [...] } } }
```

⛔ **Chi legge DEVE guardare `motivo_stop`**: un 200 non è un successo. Difetto
misurato in-app il 2026-08-21 — «Rendi definitive» mostrava il toast verde su un
lotto che il database aveva rifiutato.

⭐ **I nomi dentro `errore` sono gli stessi dell'envelope**, di proposito: a
video il gesto lo disegna un consumatore solo. Due nomi per la stessa cosa
sarebbero due strade da tenere allineate a mano.

🔴 **E dal 2026-09-09 sono le stesse anche le REGOLE — prima non lo erano.** Il
blob leggeva `exc.hint` ed `exc.targets` **diretti**, mentre l'envelope li fa
passare da `_apply_policy`, che su un codice tecnico li toglie. ⛔ Stesso nome,
regola diversa: ed è **peggio** di due nomi diversi, perché due nomi si notano e
due regole no. Da questa strada uscivano quindi un bersaglio su un guasto (un
pulsante che non doveva esserci) e il `HINT` grezzo di PostgreSQL. ⇒ Ora i due
campi si prendono da `ErrorTranslator.to_api_error(exc)`, che è la sede unica di
quelle decisioni. Presidio:
`test_il_blob_di_errore_applica_le_politiche_dell_envelope`.

⚠️ **`message` e `detail` restano invece quelli grezzi dell'eccezione**, e la
differenza è voluta: questo blob alimenta il **pannello di diagnostica di un
lotto**, dove il testo del database è l'informazione utile — non una schermata
per il cliente.

⭐ Il difetto era vivo da prima e non lo vedeva nessuno: si è reso visibile il
giorno in cui il frontend ha cominciato a **rendere** il suggerimento. *Un campo
che nessuno mostra non ha comportamenti sbagliati — ne ha di invisibili.*

**Da dove arriva `fields`, due strade:**

| Origine                         | Contratto                                                 | Stato                                                                                                                                                                                                                                                                                                                                |
| ------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| errori nati in **Python**       | `context={"field": <nome>}` nel `ServiceError`            | ✅ attivo (42 codici)                                                                                                                                                                                                                                                                                                                 |
| errori nati in **PL/pgSQL**     | `RAISE … USING COLUMN = '<colonna>'` → `diag.column_name` | ✅ **attivo dal 2026-08-24.** ⚠️ Prima diceva *«il backend lo legge già; le funzioni non lo mandano ancora»*, ed erano **due affermazioni false**: le funzioni lo mandano dall'08/08 (il ripiego su `parametro` copre quasi tutti i punti di sollevamento), ed è il **backend** a perderlo — su tre delle quattro strade di traduzione |
| **violazione NOT NULL** (23502) | `column_name` lo valorizza PostgreSQL da solo             | ✅ attivo, senza che nessuno scriva niente                                                                                                                                                                                                                                                                                            |

⭐ **Il canale del DB non è da inventare**: `COLUMN` è un campo strutturato del
`RAISE`, come `CONSTRAINT` che dal 2026-08-05 porta già il codice errore. Non
serve un parametro nuovo di `script.fn_log_and_raise_error`.

⚠️ **Sul `COLUMN` non c'è il guard sullo SQLSTATE** che invece protegge la
lettura del `CONSTRAINT`, e l'asimmetria è voluta: su un `23xxx`
`constraint_name` contiene il nome del **vincolo** (`uq_…`), che scambiato per
un codice applicativo darebbe un 500; `column_name` contiene sempre e solo un
nome di **colonna**. Non c'è un secondo significato da cui difendersi.

Analisi e ordine dei passi:
`docs/it/dev/work-done/piano-be-classe-codici-errore.md` §12.

Gli errori sono generati da:

* `ServiceError` — errori di dominio, sollevati dai service
* `ErrorManager.require(condizione, code=..., message=...)` — guard con errore strutturato
* `exception_to_error_response(exc)` — catch-all nel middleware `ApiExceptionMiddleware`

---

## Schema OpenAPI

Ogni endpoint dichiara il proprio schema con `@extend_schema` di drf-spectacular.
I serializer sono **inline** (non in file separati):

```python
@extend_schema(
    request=inline_serializer(
        name="PraticaStatoRequest",
        fields={"nuovo_stato": serializers.CharField()},
    ),
    responses={200: inline_serializer(
        name="PraticaStatoResponse",
        fields={"data": inline_serializer(name="PraticaStatoData", fields={
            "status": serializers.CharField(),
        })},
    )},
)
def post(self, request: Request, pratica_id: int) -> JsonResponse:
    ...
```

Questa scelta mantiene lo schema vicino all'implementazione, riducendo il rischio di drift.

Endpoint schema:

* `GET /api/schema/` — specifica OpenAPI 3.0 (JSON/YAML)
* `GET /api/docs/` — Swagger UI

Entrambe sono anonime (`AllowAny`: non c'e' un token da esibire) e per questo
esistono **solo** con `API_DOCS_ENABLED` (env `DJANGO_API_DOCS_ENABLED`, default
= `DEBUG`): altrove rispondono **404**, non 403. Il cancello e' request-time
(`apps/core/api/api_docs_gate.py`), presidiato da
`apps/core/tests/api/test_superficie_pubblica.py` insieme all'assenza
dell'admin Django (`/admin/` → 404, `/` → 404).

---

## Routing

### Versioning

Tutte le API canoniche sotto `/api/v1/*`. ⚠️ Le route legacy non esistono
più — sono state **rimosse**, non spente: fino al 2026-09-12 questa riga
diceva «disabilitate di default (`DJANGO_API_LEGACY_ROUTES_ENABLED=0`)», e quel
flag **non compare in nessun file del backend** (analisi-software-per-dati-morti
§4). Un documento che descrive un interruttore inesistente manda a cercarlo.

### Namespace per tipo di utente (multi-face auth)

Il refactor multi-face auth (`work-done/sviluppo-multi-face-auth.md`; il residuo in
`work-in-progress/sviluppo-multi-face-da-completare.md`) introduce
la distinzione formale tra namespace per tipo di consumatore:

| Namespace            | Base view                        | Chi accede                                                  | Stato                                                                        |
| -------------------- | -------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `/api/v1/<dominio>/` | `DomainAPIView` / `AdminAPIView` | Operatori interni (dipendenti, ruolo_applicativo=OPERATORE) | **Attivo**                                                                   |
| `/api/v1/portale/`   | `PortaleAPIView`                 | Clienti e fornitori del portale                             | **Attivo** (auth+invito+attivazione, MVP dati Stage C)                       |
| `/api/v1/shop/`      | `ShopAPIView`                    | Negozio online (pubblico + SHOP_CUSTOMER)                   | **Attivo** (auth+invito+attivazione admin-driven; catalogo/checkout Stage D) |

Le base class `PortaleAPIView` / `ShopAPIView` sono in
`apps/core/api/base_views.py`. Auth + flussi invito/attivazione dei
portali e dello shop sono operativi (PR-B + B1 §13.7). Le API di dominio
(catalogo, ordini, checkout, ricevute consumer) arrivano con Stage C/D.
Vedi [architettura-multi-face-auth](/guide/architettura-multi-face-auth).

### Convenzione URL

| Tipo              | Pattern                                              | Esempio                                    |
| ----------------- | ---------------------------------------------------- | ------------------------------------------ |
| Lista             | `GET /api/v1/<dominio>/`                             | `GET /api/v1/pratiche/`                    |
| Dettaglio         | `GET /api/v1/<dominio>/<id>/`                        | `GET /api/v1/pratiche/42/`                 |
| Azione su entita` | `POST /api/v1/<dominio>/<id>/<azione>/`              | `POST /api/v1/pratiche/42/stato/`          |
| Azione globale    | `POST /api/v1/<dominio>/<azione>/`                   | `POST /api/v1/vendite/pipeline/run/`       |
| Risorsa nested    | `GET /api/v1/<dominio>/<id>/<sotto>/`                | `GET /api/v1/pratiche/42/flussi/`          |
| Azione su nested  | `POST /api/v1/<dominio>/<id>/<sotto>/<id>/<azione>/` | `POST /api/v1/pratiche/42/flussi/7/stato/` |

I nomi usano kebab-case: `reset-draft`, `calcoli-tempo`, `regole-generazione`.

### Endpoint attivi

Per l'inventario completo degli endpoint attivi per dominio, consultare la documentazione OpenAPI generata automaticamente all'endpoint `/api/docs/` (montato solo dove `API_DOCS_ENABLED` è acceso; altrove risponde 404) oppure i documenti manuali per dominio:

* **Pratiche**: [api_coda_lavoro.md](/backend/pratiche/manual/api_coda_lavoro) | [api_competenze_flussi.md](/backend/pratiche/manual/api_competenze_flussi) | [api_definizioni_workflow.md](/backend/pratiche/manual/api_definizioni_workflow) | [api_flussi_list.md](/backend/pratiche/manual/api_flussi_list) | [api_flusso_assegnazione.md](/backend/pratiche/manual/api_flusso_assegnazione) | [api_flusso_canali.md](/backend/pratiche/manual/api_flusso_canali) | [api_flusso_detail.md](/backend/pratiche/manual/api_flusso_detail) | [api_flusso_prerequisiti.md](/backend/pratiche/manual/api_flusso_prerequisiti) | [api_flusso_riattiva.md](/backend/pratiche/manual/api_flusso_riattiva) | [api_flusso_sospendi.md](/backend/pratiche/manual/api_flusso_sospendi) | [api_flusso_stato.md](/backend/pratiche/manual/api_flusso_stato) | [api_formule_tempo.md](/backend/pratiche/manual/api_formule_tempo) | [api_genera_pratica.md](/backend/pratiche/manual/api_genera_pratica) | [api_operatori_reparto.md](/backend/pratiche/manual/api_operatori_reparto) | [api_percorso.md](/backend/pratiche/manual/api_percorso) | [api_pratica_assegnazione.md](/backend/pratiche/manual/api_pratica_assegnazione) | [api_pratica_calcoli_tempo.md](/backend/pratiche/manual/api_pratica_calcoli_tempo) | [api_pratica_detail.md](/backend/pratiche/manual/api_pratica_detail) | [api_pratica_giornale.md](/backend/pratiche/manual/api_pratica_giornale) | [api_pratica_riattiva.md](/backend/pratiche/manual/api_pratica_riattiva) | [api_pratica_sospendi.md](/backend/pratiche/manual/api_pratica_sospendi) | [api_pratica_sospensioni.md](/backend/pratiche/manual/api_pratica_sospensioni) | [api_pratica_stato.md](/backend/pratiche/manual/api_pratica_stato) | [api_pratiche_allegati.md](/backend/pratiche/manual/api_pratiche_allegati) | [api_pratiche_generate.md](/backend/pratiche/manual/api_pratiche_generate) | [api_pratiche_list.md](/backend/pratiche/manual/api_pratiche_list) | [api_pratiche_note.md](/backend/pratiche/manual/api_pratiche_note) | [api_prendi_in_carico.md](/backend/pratiche/manual/api_prendi_in_carico) | [api_regole_generazione.md](/backend/pratiche/manual/api_regole_generazione)
* **Amm. Software**: [api_amm_software.md](../backend/amm-software/manual/api_amm_software.md) — dal 2026-10-02 l'area **Accessi** (§«Area Accessi» della pagina): `accessi/altri/` e `accessi/sistema/`, le due liste che con gli operatori censiscono TUTTE le credenziali (la partizione la decide il DB, `script.fn_categoria_accesso`), e le azioni della **credenziale** — `credenziali/<id>/`, `blocca/`, `sblocca/` (`Idempotency-Key`), `secondo-fattore/…` — che valgono per tutte le sue vesti e quindi non stanno sotto `/operatori/` (il secondo fattore ci stava fino a quel giorno: ritirato). Dal 2026-09-18 anche `GET /amm-software/processi/presidi/conteggi/` (§6.1-bis): la **testata sola** dei presidi (`totale · con_righe · non_letti`) per il **pallino della topbar**, stesso giro di `presidi/` senza le prime righe, stessa porta `AdminAPIView`; un presidio non leggibile è `non_letti`, non un errore | [api_error_log.md](../backend/amm-software/manual/api_error_log.md) — dal 2026-09-19 `GET /amm-software/error-log/` (+ `export/`): la **consultazione di `dbops.error_log`** per i tecnici (pezzo E dell'osservabilità) — quale funzione ha sollevato quale codice, quando, in quale transazione — con frase, causa, soluzione e **classe** dal catalogo per JOIN e il `context` **com'è**. Ogni filtro della whitelist ha il suo indice (P-3) ed è provato con `EXPLAIN`; `function_name` è un prefisso `LIKE` con `_` escapato, `tx_id` è il ponte dal giornale di dominio. Stessa porta `AdminAPIView` dei due diari accanto; lista `dbops.error_log` esente dal perimetro emittente
* **Anagrafiche**: [api_soggetti.md](../backend/anagrafiche/manual/api_soggetti.md) | [api_clienti.md](../backend/anagrafiche/manual/api_clienti.md) | [api_indirizzi.md](../backend/anagrafiche/manual/api_indirizzi.md) | [api_indirizzi_ruolo.md](../backend/anagrafiche/manual/api_indirizzi_ruolo.md) | [api_contatti_ruolo.md](../backend/anagrafiche/manual/api_contatti_ruolo.md) | [api_conti_bancari_ruolo.md](../backend/anagrafiche/manual/api_conti_bancari_ruolo.md) | [api_conti_bancari_soggetto.md](../backend/anagrafiche/manual/api_conti_bancari_soggetto.md) (conti del soggetto, lookup IBAN e filiali) | [api_geo_config.md](../backend/anagrafiche/manual/api_geo_config.md) | [api_fornitori.md](../backend/anagrafiche/manual/api_fornitori.md) | [api_categorie_clienti.md](../backend/anagrafiche/manual/api_categorie_clienti.md) | [api_categorie_clienti_listini.md](../backend/anagrafiche/manual/api_categorie_clienti_listini.md) | [api_emittenti_fiscali.md](../backend/anagrafiche/manual/api_emittenti_fiscali.md) | [api_risorse_umane_lookup.md](../backend/anagrafiche/manual/api_risorse_umane_lookup.md) — `GET /anagrafiche/risorse-umane/lookup/`, il picker delle persone interne (responsabile commessa): cross-dominio, legge la vista modello `vw_risorse_umane_dettaglio` | [api_titoli_iva_soggetto.md](../backend/anagrafiche/manual/api_titoli_iva_soggetto.md)
* **Config**: [api_utilities_tipi_ruolo.md](/backend/config/manual/api_utilities_tipi_ruolo) | [api_tipi_ruolo_tipi_indirizzo.md](/backend/config/manual/api_tipi_ruolo_tipi_indirizzo)
* **Catalogo**: [api_catalogo.md](/backend/catalogo/manual/api_catalogo) — articoli (CRUD, lista `catalogo.articoli` id 26, UoM operative, BoM, note): oltre alla natura di vendita (*dove va* la riga) l'articolo dichiara **da dove arriva** — `modo_approvvigionamento_id` (lookup generico `rel=config.modi_approvvigionamento`, default `ACQUISTO`), `gestito_a_magazzino` (default `false`, fail-safe) e `lead_time_giorni` (nullable per modello). ⚠️ `ARTICOLI_DETAIL_COLUMNS` è una proiezione **per nome** da `vw_articoli_dettaglio`: una colonna nuova della vista non esce finché nessuno la nomina
* **Auth**: [api_multi_veste_token.md](/backend/core/manual/api_multi_veste_token) | [auth_views_audit.md](/backend/core/manual/auth_views_audit) | [api_user_profile.md](/backend/core/manual/api_user_profile) | [api_token_cambio_password.md](/backend/core/manual/api_token_cambio_password) | [api_password_reset.md](/backend/core/manual/api_password_reset) | [api_invito_operatore.md](/backend/core/manual/api_invito_operatore) | [api_invito_portale_shop.md](/backend/core/manual/api_invito_portale_shop) | [api_logout.md](/backend/core/manual/api_logout) | [api_secondo_fattore.md](/backend/core/manual/api_secondo_fattore) | [api_sessioni_attive.md](/backend/core/manual/api_sessioni_attive) | [api_permessi_effettivi.md](/backend/core/manual/api_permessi_effettivi) — le rotte proprie di portale e shop (attivazione, `register/check-email/`, `profile/activate-shop/`) stanno in `api_invito_portale_shop.md`
* **Core — Ricerca universale**: [api_search_universale.md](/backend/core/manual/api_search_universale)
* **Email**: [api_email.md](/backend/core/manual/api_email) — dal 2026-09-26 la famiglia `/core/email/` ha una porta: `GET /core/email/log/` (+ `log/stati/`) e' aperta a **ogni operatore** (`skip_area_check`, sola lettura) e la consuma la voce frontend Strumenti › Email (voce senza `requireArea`; il dominio «Personale» del 2026-09-26 e' stato assorbito in Strumenti lo stesso giorno). Chi vede quale mail lo decide la RLS per ambito (`script.fn_scope_email_ambito`: SISTEMA al super admin, REPARTO al reparto, OPERATORE all'autore, sempre in AND con l'emittente), non la view. ⛔ Bozze e invio restano sotto l'area `config` finche' non esiste l'azione di processo `invia_email`
* **Parametri**: [api_parameter_settings.md](../backend/core/manual/api_parameter_settings.md)
* **Core — Lookup dedicati**: [api_lookup_dedicati.md](../backend/core/manual/api_lookup_dedicati.md) — tipi soggetto dettaglio, tipi ruolo per natura, forme giuridiche, utility per emittente, conti contabili, sistema codici, comuni
* **Core — Lookup tipi di entità**: [api_tipi_entita_lookup.md](../backend/core/manual/api_tipi_entita_lookup.md) — dal 2026-09-19 `GET /core/lookup/tipi-entita/`: il vocabolario **vivo** di `config.tipi_entita` con l'`etichetta_key` che il DB dichiara. ⛔ Lookup dedicato perché la tabella non ha `id`/`descrizione`. Nasce perché la tendina «Entità» del giornale trasversale si era ricopiata sette codici su nove: un vocabolario del DB si legge, non si specchia
* **Core — Lookup azioni di riga**: [api_azioni_riga_lookup.md](../backend/core/manual/api_azioni_riga_lookup.md) — dal 2026-10-27 `GET /core/lookup/azioni-riga/`: il registro `config.azioni_riga` in sola lettura (`codice_interno`, `colonna_motivo`, `colonna_motivo_chiave`). Il BB FE `useAzioneRiga` ne legge quali colonne della riga portano il motivo di un pulsante spento: un'azione di riga nuova è una riga di registro, non un pulsante nuovo (brief-modello-documento-vendita §15.11, BE-3)

#### Vendite: documenti, fatturazione e commesse

* **Vendite — Pricing v5**: [api_preventivi.md](/backend/vendite/manual/api_preventivi) | [api_listini.md](/backend/vendite/manual/api_listini) | [api_contratti.md](/backend/vendite/manual/api_contratti) | [api_promo_articoli.md](/backend/vendite/manual/api_promo_articoli) | [api_pricing.md](/backend/vendite/manual/api_pricing) | [api_approvazioni_prezzo.md](/backend/vendite/manual/api_approvazioni_prezzo) | [api_vendite_lookups.md](/backend/vendite/manual/api_vendite_lookups) | [api_vendite_form_defaults.md](/backend/vendite/manual/api_vendite_form_defaults) | [api_registri_numerazione.md](/backend/vendite/manual/api_registri_numerazione) | [api_famiglie_documento.md](/backend/vendite/manual/api_famiglie_documento) — il CRUD delle famiglie di documento (`/vendite/famiglie/`, `AdminAPIView`): la creazione passa dalla madre `fn_crea_famiglia_documento`, che provvede anche i registri; `colonna_billing_account` è **facoltativa** come `colonna_serie` (`NULL` = «questa famiglia non ha un billing account», la forma dell'ordine di acquisto)
* **Vendite — Ciclo attivo**: [api_offerte.md](/backend/vendite/manual/api_offerte) | [api_ordini.md](/backend/vendite/manual/api_ordini) | [api_ddt.md](/backend/vendite/manual/api_ddt) | [api_resi.md](/backend/vendite/manual/api_resi)
* **Vendite — Fatture, lotti e pipeline**: [api_fatture_list.md](/backend/vendite/manual/api_fatture_list) | [api_lotti_list.md](/backend/vendite/manual/api_lotti_list) | [api_run_lotto_pipeline.md](/backend/vendite/manual/api_run_lotto_pipeline)
* **Vendite — Lotto: i documenti PRESI IN CARICO**: [api_lotto_gruppi_list.md](/backend/vendite/manual/api_lotto_gruppi_list) — `GET /vendite/lotti/<id>/gruppi/` (+ `/export/`): che cosa il lotto ha preso in carico e com'è andato ciascun documento, **compresi quelli che una fattura non sono mai diventati**. ⛔ Non è un doppione di `/fatture/`, ed è la ragione per cui esiste: quella lista si aggancia a `fattura_id`, quindi un documento caduto PRIMA che una fattura esista non ha niente a cui appendersi — sul lotto LTF-0009578 se ne vedevano due su tre, e il terzo era nominato solo da una segnalazione, con l'identificativo della COMMESSA. ⚠️ Le due liste non sono in corrispondenza 1:1 nemmeno a giro riuscito (`fn_build_fattura_key` può raccogliere più gruppi nello stesso documento): sono due domande diverse. ⭐ La risposta porta **`perimetro_dichiarato`**, e senza quel flag «non ha lavorato niente» e «non dichiara un perimetro» si leggono uguali — un giro DI MASSA non scrive nessun gruppo, perché l'assenza di righe È il criterio (garanzia G1). 🔒 Il cancello di scope è la TESTATA, e il JOIN vale anche per il conteggio (dal 2026-09-10 anche `fatturazione_lotti_gruppi` porta il perimetro: §Enforcement RLS). ⚠️ L'ordine di default non è alfabetico ma «i falliti in cima»: `ERRORE` ordinato per stringa verrebbe dopo `COMPLETED`, cioè il caso che interessa finirebbe in fondo
* **Vendite — Cockpit fatturazione (Fase C)**: [api_fatturazione.md](/backend/vendite/manual/api_fatturazione) — endpoint di comando del cockpit: giro «Fattura competenza» (`POST fatturazione/run/`, non bloccante via coda lavori `dbops.coda_lavori`) + polling `run/<job_id>/`, «Rendi definitive» perimetro (`POST fatturazione/numera/`) e singolo lotto (`lotti/<id>/numera/`), ristampa massiva (`lotti/<id>/ristampa/`), esiti giri + stato coda stampa (`fatturazione/esiti/`). Dal 2026-07-27 `fatturazione/run/` accetta `gruppi[]` = **emissione mirata** (stesso verbo, perimetro ristretto ai gruppi fatturabili scelti; assente = giro di massa invariato). Dal 2026-11-07 run e numera accodano **un lavoro per azienda** (risposta `{lavori: [...]}`, selezione divisa per azienda) e il polling è per azienda (BE10 a). Idempotenza 2-layer, identità operatore catturata (RLS come nel web), gate fiscale I-7
* **Vendite — Commesse (governo operativo)**: [api_commessa_stato.md](/backend/vendite/manual/api_commessa_stato) — dal 2026-09-14 il dettaglio porta anche la **testata leggibile** (`descrizione`, `data_apertura`, responsabile — Blocco C di `brief-db-modifiche-certe-ciclo-vendita-e-articolo`) e `PATCH /commesse/<id>/` la scrive (parziale; `data_apertura` in sola lettura; il responsabile deve essere una risorsa umana **attiva**: lo dice il require DB, 409 `E_ATTIVO_PADRE_NON_ATTIVO` col campo, dal 2026-11-07). Il picker è `GET /anagrafiche/risorse-umane/lookup/`. ⭐ Dal 2026-10-12 l'**annullo** della commessa passa dal verbo `vendite.fn_annulla_commessa` con la conferma dei legami (`GET /commesse/<id>/legami/` + `legami_confermati`, la stessa forma di bolla, ordine, preventivo e contratto): annullare riapre a monte ciò che l'ha riempita (brief-db-annullo-a-valle-riapre-a-monte) | [api_commessa_attivita.md](/backend/vendite/manual/api_commessa_attivita) — lista righe + azioni APPROVA (riga/mese) e, dal 2026-07-28, **ANNULLA riga manuale** (`POST /commesse/<id>/attivita/<att_id>/annulla/`): non cancella, porta `stato_emissione` ad `ANNULLATA` (valore già filtrato da tutte le porte verso fattura e cockpit) con motivo obbligatorio tracciato; gate `carica_voce_manuale`, perimetro = righe sourceless non emesse su commessa modificabile | [api_commesse_pricing.md](/backend/vendite/manual/api_commesse_pricing) — azioni prezzo N5/N7/sblocco, dal 2026-07-23 gated su azione di processo **`prezzo_override_manuale`** (stesso codename dei gate prezzo di preventivi/contratti/DDT) | [api_commessa_oneri.md](/backend/vendite/manual/api_commessa_oneri) — **porta oneri**: `POST /commesse/<id>/oneri/` crea la riga di puro valore (qta=1, `tipo_movimento=ONERE`, già APPROVATA, sourceless), causale/UoM/IVA derivate dall'articolo-onere dalla madre DB; gate `carica_voce_manuale`, presidio all'ingresso senza approvazione a due passi
* **Vendite — registro delle righe di commessa**: `GET /vendite/commesse/<id>/registro/` (opz. `commessa_attivita_id` per una riga sola, `limit`/`offset`) espone gli eventi che il database scrive su `vendite.commesse_attivita_log` — oneri aggiunti, righe annullate a mano, **ritirate alla chiusura del documento di origine**, riportate «da emettere», accrediti. Risponde a «perché questa riga è così»: chi, quando, con quale **motivo**. ⛔ **Lo scope sta sulla riga di commessa, non sul log**: il `JOIN` è il cancello e vale anche per il **conteggio** (un totale senza cancello direbbe «12 eventi» mostrandone 3). Dal 2026-09-10 anche `commesse_attivita_log` porta il perimetro (§Enforcement RLS): l'ordine resta, il fail-open no. È la stessa lezione di `attivita_fatturabili`. ⚠️ Il vocabolario degli eventi è del DB ed è **aperto**: la query non ne nomina nessuno e non filtra, così un evento nuovo compare da sé; il frontend lo risolve con ripiego sul codice grezzo. 🔴 Nasce il 2026-08-28 perché quella tabella **si scriveva e non si leggeva**: sei tipi di evento irraggiungibili da qualunque schermata, e una guida che prometteva il contrario.
* **Vendite — «Riporta da emettere» (recupero delle attività residue)**: [api_riporta_da_emettere.md](/backend/vendite/manual/api_riporta_da_emettere) — `POST /vendite/attivita-fatturabili/riporta-da-emettere/` (permesso dedicato `riporta_da_emettere`, `Idempotency-Key` obbligatoria) rimette in coda di fatturazione un elenco di attività **residue** e riporta a `NON_EMESSA` le righe di commessa passate a `EMESSA` per causa loro. ⛔ Non ricrea lotti né fatture: il lavoro ricompare in «Da emettere» e segue il giro normale. ⭐ **Sincrono** — due scritture e una transazione, nessun job: accodarlo per simmetria con «Rendi definitive» importerebbe la dedup, che qui non esiste. Il compagno `riportabili/` restituisce i **motivi ostativi** senza tentare nulla (è un POST pur essendo una lettura: una selezione di 200 righe non sta in una query string) e porta lo **stesso permesso del verbo** — dichiarato a mano, perché senza `post_permission` un POST cadrebbe su `add` d'area, che è il gate sbagliato nei due versi. Serve a **spiegare invece di far fallire** — incontrare `E_ATTIVITA_GIA_DA_EMETTERE` significa che l'elenco a schermo era invecchiato — e il frontend lo chiama **prima** di ogni riporto: la mutazione è atomica, quindi senza quel passo il rifiuto arriverebbe come *un* errore per l'intero elenco e chi guarda non saprebbe quale riga lo ha fermato. 🔴 Lo **scope sta sulla commessa**, non sull'attività: la riga di commessa è il cancello, e il danno di sbagliarlo sarebbe lo **stato spezzato** (attività liberata, riga di commessa no). Dal 2026-09-10 anche `attivita_fatturabili` porta il perimetro (§Enforcement RLS). ⚠️ Il perimetro **non usa `fatturato`**, che dal `20260826-33` è una colonna generata: un verbo fondato lì smetterebbe di funzionare in silenzio.
* **Vendite — Fattura (consultazione)**: [api_fattura_dettaglio.md](/backend/vendite/manual/api_fattura_dettaglio) — `GET /vendite/fatture/<id>/` restituisce il **documento completo** (testata decodificata + righe da `vw_fattura_righe_esposte` con kit risolti + riepilogo IVA + piano rate) in un round-trip, per il drawer di consultazione. Orchestra gli **stessi** lettori che alimentano il contesto del PDF → video e stampa raccontano lo stesso documento per costruzione (regola R17). Sola lettura: oltre EMESSA le righe sono congelate a DB. ⚠️ **Ordine di lettura vincolante**: prima la testata — fuori scope è un 404, non un documento vuoto (righe e riepiloghi portano il perimetro dal `20260729-05`: la frase «no» era stantia da luglio — §Enforcement RLS). Include le note fattura (`<id>/note/`, sesto dominio del BB partizionato) e i `contatori` dei badge (oggi `note`) — dict e non scalare per reggere i prossimi senza cambiare shape; il conteggio sta **dopo** il cancello di testata, così un documento fuori scope non conta niente (dal 2026-09-09 anche `note_fatture` porta il perimetro)

#### Vendite: giornali, situazioni e cruscotti

* **Vendite — Giornale trasversale degli eventi**: [api_giornale.md](/backend/vendite/manual/api_giornale) — dal 2026-09-19 `GET /vendite/giornale/` (+ `export/`): «cosa è andato storto, su tutto, nell'ultimo periodo» — la Storia di tutte le entità insieme filtrata per gravità (default `ERROR`, che **include** la gravità `NULL`), per registro, tipo di entità, date e **filo** (`tx_id` o `correlation_id`), con `entita_display` risolto nel backend e `ritirate_count`. ⭐ **Terzo lettore** di `script.vw_giornale_entita` sullo stesso corpo dei due per entità — non un aggregato nuovo. ⛔ Niente `context`/`payload`: la lista è una vetrina, la Storia dell'entità è il pezzo forense. 🔒 Il perimetro lo applica la vista (`security_invoker`) riga per riga e nei conteggi, ed è **provato** sul DB vero con due emittenti costruiti (pezzo G dell'osservabilità)
* **Vendite — Giornale fattura (la storia del documento)**: [api_fattura_giornale.md](/backend/vendite/manual/api_fattura_giornale) — `GET /vendite/fatture/<id>/giornale/`: «cosa è successo a questo documento, in ordine di tempo», elenco paginato di sola lettura che alimenta la scheda «Storia» del drawer fattura. ⭐ **Primo consumatore di `script.vw_giornale_entita`** (la vista che cuce i quattro registri di evento): fino al 2026-08-24 il suo perimetro era verificato dal pgTAP e non dall'uso. ⛔ Da non confondere con `/passaggi/`, che dice con quali **altri documenti** la fattura è legata: qui si risponde a *«cosa le è successo»*. 🔴 **Il cancello è la testata**: la vista è `security_invoker` e su una fattura fuori scope risponderebbe **zero righe** — cioè «non è successo niente» invece di «non la vedi». Il 404 nasce da `vendite.fatture`, non dalla vista. ⛔ L'ordine **non può appoggiarsi al solo tempo** (`now()` è il timestamp di transazione: 38 righe su 3 istanti), a ordinare dentro l'istante è il tiebreak. ⚠️ Le segnalazioni **ritirate** sono nascoste di default e `ritirate_count` dichiara quante: senza quel numero «nessun evento» e «tre eventi tutti superati» si leggono uguali
* **Vendite — Fondi fattura (governo)**: [api_fondi_fattura.md](/backend/vendite/manual/api_fondi_fattura) — `GET /vendite/fondi-fattura/da-decidere/` (+ `/export/` CSV/XLSX, colonne dalla configurazione lista dell'operatore): l'elenco dei casi in cui il giro automatico **si ferma** e la scelta resta a una persona (4 motivi a vocabolario chiuso). Read-only su `vw_fondi_fattura_da_decidere`, `security_invoker` → **va letta con la connessione dell'utente, mai da un canale di sistema**. ⭐ L'elenco **presenta, non sana**: nessuna riga ha un gemello automatico che la corregge, perché sanarla vorrebbe dire muovere denaro senza che nessuno l'abbia deciso. ⭐ **E un verbo, dal 31-08-2026**: `DELETE /vendite/fondi-fattura/<id>/` cancella un atto che non e' ancora diventato un fatto — il **metodo dice il verbo**, e §Grammatica URL vieta di scriverlo nel path. `post_permission = governa_fondo_fattura` (azione «pericolosa») e `Idempotency-Key` obbligatoria, perche' il gesto e' irreversibile. ⛔ **Non serve al riporto sbagliato**: quello si disfa annullando la sistemazione che lo ha creato, e il rifiuto **nomina** quella strada invece di dire «non si puo'». Il criterio del rifiuto sta in **una sede sola** a database (`fn_check_fondo_cancellabile`, sei motivi), quindi il backend **non ne tiene una copia**: traduce e passa
* **Vendite — Situazione merce (ordine e DDT)**: [api_situazione_merce.md](/backend/vendite/manual/api_situazione_merce) — `GET /vendite/{ordini|ddt}/<id>/situazione-merce/`: quanto è uscito, tornato, fatturato e cosa resta aperto, in **un round-trip** e quattro sezioni (riassunto per riga d'ordine · partite di merce · coda accrediti · coda ri-consegne). Read-only su `vw_situazione_merce_ordine` + `vw_partite_merce` + le due code, tutte `security_invoker`. Le due view nascono dal factory `build_situazione_merce_view` (i domini sono due dal primo giorno). ⛔ **`differenza` e `da_spedire` possono essere `null`, e `null` non è zero** («il conto non si applica»: ordine non ancora impegnato, riga mai spedita, causale non fatturabile, conto non calcolabile) e **`stato` non si ri-traduce** — arriva già tradotto dal DB con **sette** valori. ⚠️ `fatturato_anticipato` non è un accredito. 🔴 Il perimetro si verifica sulla **testata** prima di ogni lettura: fuori scope → 404, altrimenti il pannello uscirebbe vuoto invece che negato (dal 2026-09-09 anche le righe di `ordini`/`ddt` portano il perimetro: §Enforcement RLS)
* **Vendite — Lineage/genealogia documenti**: [api_lineage_passaggi.md](/backend/vendite/manual/api_lineage_passaggi) — `GET /<dominio>/<id>/passaggi/` sugli 8 domini (7 documenti + commessa — factory `build_passaggi_view`): pratica collegata + frontiera + catena transiti avanti/indietro (read-only su `vw_documento_lineage`/`fn_documento_lineage`, RLS invoker)
* **Vendite — Situazione aperta**: [api_dashboard_aperto.md](/backend/vendite/manual/api_dashboard_aperto) — stock documenti per `area × fase` senza asse temporale + drill-down (read-only su `vw_dash_aperto_*`; sostituisce la dashboard 5-card, Fase 3 due-lenti)
* **Vendite — Dashboard competenza (Lente 1)**: [api_dashboard_competenza.md](/backend/vendite/manual/api_dashboard_competenza) — funnel commessa→fattura per mese di competenza: aggregata 12 mesi × 4 stadi + breakdown stato fattura, drill-down attività, drill-down per commessa, **gruppi fatturabili** (`gruppi/` — l'unità dell'emissione mirata: documento sorgente oppure oneri di commessa, con riepilogo di perimetro nell'envelope; la `gruppo_key` è la stessa accettata da `fatturazione/run/`), errori vivi, e dal 2026-08-27 i **residui** (`residui/` + `residui/export/` — le attività che una fattura non ce l'hanno più e che nessun giro riprenderà da solo: è l'elenco su cui agisce «Riporta da emettere». ⛔ Non è un filtro di `attivita/`: lo stadio `EMESSA_NON_FATTURATA` contiene **quattro** situazioni e solo `RESIDUO` chiede un'azione — esporre un parametro per sceglierla darebbe l'illusione di poter allargare il perimetro del verbo, che invece lo decide il modello. ⚠️ Default `competenza_mese` **ASC** e non `valore` DESC come le liste sorelle: non è una lista di grandezze, è una **coda di recupero** — il residuo più vecchio è il più vicino al limite di emissione) (read-only su `vw_dash_competenza_*`)
* **Vendite — Dashboard backlog (Lente 2)**: [api_dashboard_backlog.md](/backend/vendite/manual/api_dashboard_backlog) — non-collegati per anzianità + classe di azionabilità: contatori 🟠/🔵/🔴 + lista con motivo/azione (read-only su `vw_dash_backlog_*` + lookup `config.motivi_fermo`)

#### Pagamenti, magazzino e documenti

* **Pagamenti — il giro degli incassi** (registrato qui il 2026-09-12: le 25 rotte erano in esercizio dal 2026-08-24 e nessuna pagina le nominava — `copertura_doc_api` dava l'area al **4%**): [api_pagamenti.md](/backend/pagamenti/manual/api_pagamenti) — una pagina sola per il dominio, come per la generazione documenti: la **distinta** (`distinte/`, `<id>/stato/`, e dal 2026-09-18 le righe come **lista configurabile** `distinte/<id>/righe/` + `export/` — lista `pagamenti.distinta_righe`, paginata, «la contabile in CSV/Excel»; fino a quel giorno viaggiavano dentro il dettaglio, su una `DataTable` grezza senza pagina né export), la **registrazione** (`anteprima-registrazione/`, `registra/` — una sola `SELECT` sulla madre, esito `NULLA_DA_POSTARE` che risale intatto — e la **correzione guidata** `correggi/`), l'**abbinamento** (`righe/<id>/abbina/` con la forzatura a due tempi: `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` è il primo codice con `ui_action = confirm_and_retry`), le due **code** (`righe/?coda=`), `rate/fuori-capienza/`, la **base dei saldi** a tre livelli (`rate/<id>/saldo/`, `fatture/<id>/saldo/`, `fatture/<id>/rate/` — sede unica, forma unica `residuo · in_lavorazione · incassato`; `escludi_riga_id` = «prima di sé» sulla rata dal 17/09 e sul documento dal 18/09, stesso parametro dichiarato una volta) e dal 2026-09-17 la sua **quarta lettura**, `rate/` — l'elenco paginato delle rate col saldo (lista `pagamenti.rate`), sorgente del **picker** della distinta e dello scadenzario: pagina prima, saldo dopo dal nucleo `fn_get_saldi_rate` con l'array degli id, numero fattura **esatto** (101 non porta 1010), «aperta» = `residuo <> 0`, e dal 18/09 `solo_numerate` — le rate delle **bozze** fuori, il picker lo passa sempre; e il verbo di collezione `distinte/<id>/righe/da-rate/` — **N rate scelte → N righe** con esito **PARZIALE per riga** via `run_fan_out`, ogni fallita col suo errore intero (`ui_action` compresa: il secondo tempo della capienza è per riga) —, le **sistemazioni** (`eccedenze/`, `sistemazioni/` + `conferma/`/`annulla/`, `fatture/<id>/sistemazioni/` + `export/`) e i **canali di incasso** (`enti-incasso/`, `conti-incasso/`). ⚠️ Le quattro rotte `fatture/<id>/…` hanno `skip_area_check`: le consuma il drawer fattura di `vendite`, che non può chiamare `pagamenti` lateralmente. 🔴 `registra/` e `correggi/` sono gated su `registra_distinta`, fail-closed finché l'azione non è assegnata a un profilo
* **Magazzino — le anagrafiche** (2026-09-21, [piano](work-done/piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md)): [api_anagrafiche_magazzino.md](/backend/magazzino/manual/api_anagrafiche_magazzino) — `GET/POST /magazzino/magazzini/` (+ `export/`, `<id>/` GET/PATCH), le ubicazioni **sotto il padre** `GET/POST /magazzino/magazzini/<id>/ubicazioni/` (+ `export/`, `<uid>/`), i lotti **per articolo** `GET/POST /magazzino/lotti/?articolo_id=` (+ `export/`, `<id>/`). Liste a catalogo 80-82; RLS sull'emittente del magazzino (404 no-leak, `E_MAG_*_NON_TROVAT*`), `lotti` senza perimetro (`perimetro_emittente = false`). Il documento interno, i lookup di riga e la consultazione hanno la loro pagina (riga sotto).
* **Magazzino — il documento interno e la consultazione** (2026-09-25, [piano Lotto 2](work-done/piano-be-fe-magazzino-lotto-2-motore.md)): [api_magazzino.md](/backend/magazzino/manual/api_magazzino) — inventario e rettifica come **una famiglia** (`FamigliaDocumentoInterno`, rotte sotto `/magazzino/{inventari|rettifiche}/` dalla stessa factory): lista + `export/`, crea/dettaglio/`PATCH`/`DELETE`, `<id>/stato/`, **`<id>/registra/`** (il gesto irreversibile: `post_permission = registra_magazzino` **e** lo stesso controllo dentro il verbo a DB), righe (lista, `export/`, CRUD), e solo per l'inventario `<id>/piano/` (+ `export/`). Il dettaglio porta il blob `capabilities` di `fn_available_actions_<famiglia>` **intatto**, con la terna `can_registra*`. L'anteprima `righe/motivi/` è `fn_check_riga_magazzino` così com'è; tre lookup di riga dedicati (ubicazioni, lotti, seriali). Consultazione: `disponibilita/` (+ `articoli/`, `blocchi/`), `movimenti/` (con `inventario_id`/`rettifica_id` per il deep-link dal documento registrato). Liste a catalogo 70-77. Scritta il 2026-09-25: le rotte erano in esercizio dal 2026-09-18 senza una pagina che le nominasse.
* **Documenti**: [api_documenti_templates.md](/backend/documenti/manual/api_documenti_templates) — il motore documentale: template (CRUD della testata, i modelli **standard** senza emittente e `personalizza/` che ne copia uno per un emittente), versioni (CRUD, `clona`, `pubblica`), asset (upload multipart, PATCH, download, miniatura) e `context-builders`. [api_documenti_per_sorgente.md](/backend/documenti/manual/api_documenti_per_sorgente) — le rotte documenti dei sei domini sorgente. Building block trasversali per view "per sorgente" (offerta/preventivo/contratto): [api_documenti_helpers.md](/backend/documenti/manual/api_documenti_helpers) — `resolve_contesto_documentale` + `extract_allegati` (2026-05-28). **Ristampa fedele** (2026-08-03): [api_ristampa_fedele.md](/backend/documenti/manual/api_ristampa_fedele) — `GET .../documenti/<id>/ristampa/` sui 6 domini sorgente: ri-renderizza il documento **com'era** (versione di template pinnata, anche OBSOLETA + `context_json` congelato), senza persistere nulla. È il terzo percorso, distinto dallo **scarica originale** (`file/`, richiede il file su storage: la persistenza è iniziata il 2026-07-21) e dal **genera nuovo documento** (`genera/`, modello e dati di oggi — che fino al 2026-08-03 si chiamava impropriamente «ristampa»). Fedeltà dichiarata in header `X-Ristampa-Pdf-Hash-Match`: byte diversi = fedele nel contenuto, non un errore.
* **Core — Gestione code (tracciamento)**: [api_gestione_code.md](/backend/core/manual/api_gestione_code) — badge conteggi code + liveness worker (`tracciamento/code/conteggi/`), liste coda lavori/stampa (`tracciamento/coda-lavori/`, `tracciamento/coda-stampa/`, scope operatore, `?ambito=tutti` con `code_manage`), dettaglio job e azioni `annulla/`/`requeue/` (ownership scope-based BE, 404 no-leak). ⭐ Dal 2026-09-04 anche l'**archiviazione** — `archivia/` e `ripristina/` su **entrambe** le code, rotte di **collezione** (`{"ids": [...]}`, tetto 200, dedup) perché il gesto è di massa e il menu di riga manda un elenco di uno: toglie una riga dall'**elenco** senza toccarne lo **stato**, perché i conteggi del pannello «Esiti fatturazione» sono un `GROUP BY` sullo stato **senza filtro di visibilità** e qualunque cancellazione o annullamento li sposterebbe. ⛔ Gate **`code_manage`** e non l'ownership degli altri due verbi: l'effetto è **globale** (chi archivia toglie la riga anche all'amministratore), e un verbo globale in un modello di permessi per-proprietario non compone. ⛔ Il criterio «solo una riga non viva si archivia» sta nel **trigger** (`dbops.trgfn_coda_archiviazione`, una funzione per due code) più il `CHECK`: il backend traduce `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` (409) e passa, senza tenerne una copia — e nemmeno scrive `archiviato_il`/`archiviato_da`, che le deriva il trigger dalla GUC. ⚠️ Le liste nascondono le archiviate di default (`?archiviate=1` le chiede) e dichiarano **`archiviate_count`**: senza quel numero «coda pulita» e «tre righe messe via» si leggono uguali. ⛔ E la bandiera **non entra** nel `WHERE` di claim, drainer, reaper, `mark_*` e `count_*`: è la cosa che distingue l'archiviazione da un annullamento silenzioso. ⛔ **Esito PARZIALE via `run_fan_out`** (un savepoint per riga): il rifiuto è per riga, quindi venti archiviazioni buone non si perdono per una riga tornata al lavoro — chi consuma guarda `esito` e `falliti[]`, non lo status. È anche la ragione per cui non si fa un solo `UPDATE … WHERE id = ANY(…)` col predicato di stato: sarebbe la seconda copia di «riga viva». ⭐ **Dal 2026-09-06 la soglia di liveness del badge non è più un numero nel backend**: arriva dal *dichiarato di deploy* (`backend/deploy/sveglie.json`, campo `tolleranza_minuti`) via `apps.core.services.sveglie` — vedi [sveglie_processi.md](/backend/core/manual/sveglie_processi). Il valore a video non cambia (10 minuti per entrambi i drainer): cambia **chi lo dice**. Prima era `WORKER_ATTIVO_SOGLIA_MINUTI = 10` accanto a un commento che spiegava la scelta con l'`OnCalendar` scritto in un ALTRO file — cioè lo stesso fatto in due sedi che non si conoscevano, e la divergenza sarebbe stata **muta**: un pallino verde su un worker fermo. ⚠️ Il contratto della risposta per worker è `{last_run_at, attivo, in_corso, ultima_conclusa}` — dal 2026-09-14 senza `last_ok`, che era l'esito di una corsa accanto alla data di un'altra (dettaglio in [api_gestione_code.md](/backend/core/manual/api_gestione_code) §1)
* **UI — Personalizzazioni liste (runtime)**: [api_ui_liste.md](/backend/ui/manual/api_ui_liste) — risoluzione configurazione lista, catalogo modale, UPSERT/DELETE preferenza utente, e dal 2026-09-30 `GET /ui/misure-pagina/`: le misure «righe per pagina» e i due default dal catalogo DB `ui.misure_pagina`, per **tutti** i paginatori (il frontend le legge una volta per sessione). Meta-API trasversale (`skip_area_check=True`).
* **UI — Dashboard (preferenze e contatori)**: [api_ui_dashboard.md](/backend/ui/manual/api_ui_dashboard)
* **UI — Export liste**: [api_export_liste.md](/backend/ui/manual/api_export_liste) — il BB comune e l'elenco degli export serviti.
* **UI — Personalizzazioni liste (admin Blocco F)**: [api_ui_admin_personalizzazioni.md](/backend/ui/manual/api_ui_admin_personalizzazioni) — Fase 1: CRUD preset (testata + composizione atomica) + UPSERT/DELETE permessi colonna; auth via azioni di processo `ui_preset_manage`/`ui_permesso_manage` o SUPER_ADMIN. Fase 2 (DEF-5b 2026-05-10): CRUD `ui.lista_definizione` + `ui.lista_colonna` SUPER_ADMIN-only via `AdminAPIView`.
* **UI — Export liste (DEF-1, 2026-05-10)**: endpoint dedicato per dominio (`GET /api/v1/anagrafiche/clienti/export/?formato=csv|xlsx`, `GET /api/v1/anagrafiche/soggetti/export/?formato=csv|xlsx` dal 2026-05-11, `GET /api/v1/anagrafiche/fornitori/export/?formato=csv|xlsx` dal 2026-05-24, `GET /api/v1/vendite/contratti/export/?formato=csv|xlsx` dal 2026-06-02; estensione altre liste in DEF-8). Renderer puro generico `apps.ui.services.lista_export_service.ListaExportService` no-fetch: riceve righe + config colonne + filtri applicati, produce bytes CSV (BOM UTF-8 + header `#` JSON filtri) o XLSX (foglio "Dati" + foglio "Filtri applicati", styling header bold). Hard cap 10.000 righe, errori `E_UI_EXPORT_LIMIT_EXCEEDED` (422) / `E_UI_EXPORT_FORMAT_INVALID` (400) / `E_UI_EXPORT_FAILED` (500). Niente SQL dinamico sulla `vista_sql`: ogni dominio chiama il proprio repository esistente e delega al renderer. **Coda invariante estratta** (regola del 2, 2026-06-02) in `apps.ui.api.export_helpers.{parse_export_format,build_export_response}`: ogni view export mantiene solo il parsing dei propri filtri + la chiamata al service con `limit=EXPORT_MAX_ROWS+1`; validazione formato, guard limite, risoluzione colonne dalla config runtime, render e `HttpResponse` vivono nel building block. ⭐ **La view `…/export/` dichiara LO STESSO `lista_codice` della lista accanto** — e dal 2026-09-18 lo pretende un presidio che legge le coppie dalle rotte (`apps/core/tests/test_export_lista_codice_pari.py`, 28 coppie): due letterali uguali divergono al primo rename senza nessun errore, e il file avrebbe le colonne di un'altra lista. La forma che non diverge è `lista_codice = ApiLista.lista_codice` (`distinta_righe`, `sistemazioni_fattura`). ⭐ **La ricerca libera nel file la dichiara il BB, non la view** (2026-09-29, regola del 2): `build_export_response` passa al renderer `filtri_export_con_ricerca(request, …)`, che legge `search` dalla richiesta e lo scrive come `"Ricerca"` **solo se ha filtrato davvero** (dopo lo `strip`, alla soglia della lista — `soglia_ricerca`, la stessa di `add_ricerca_full_condition`); le chiavi `search`/`Ricerca` eventualmente messe dal caller si tolgono, così non compare due volte. Le view dichiarano solo i **propri** filtri (i `resolve_filtri_export_label` non hanno più il parametro `search`). Prima la dichiaravano le view, a modo loro, e chi se ne dimenticava (righe distinta, righe inventario/rettifica, righe dei documenti di vendita) consegnava un file filtrato con `# Filtri applicati: {}`. ⚠️ Invariante: una lista con colonne `ricercabile_full` applica `search` anche nell'export — il file è la lista che l'operatore vede.

* **AI Assistant** (registrato qui il 2026-09-09: l'app esisteva e questo elenco non la nominava): [api_ai_query.md](/backend/ai-assistant/manual/api_ai_query) | [api_ai_status.md](/backend/ai-assistant/manual/api_ai_status) | [ai_tool_registry.md](/backend/ai-assistant/manual/ai_tool_registry) — `POST /api/v1/ai-assistant/query/` (linguaggio naturale + function calling su 18 tool di dominio) e `GET .../status/`. ⛔ **Le rotte sono montate solo se `AI_ENABLED=1`**: a flag spento l'app non e' nemmeno in `INSTALLED_APPS`. ⭐ L'assistente si concede per area come ogni dominio: `ai_assistant` e' a catalogo dal 2026-09-25 (riga 14 di `config.aree_funzionali`). `LETTURA` consulta, `TUTTO` anche agisce (i tool di scrittura, sempre con conferma), `BLOCCATO` non entra; vale sempre il piu' stretto fra questo livello e quello del dominio del tool. L'ingresso chiede `view` (`post_accesso = "view"`: una domanda e' una lettura), e `status/` dice in anticipo se l'utente e' dentro (`utilizzabile`), cosi' la topbar mostra la chat solo a lui. ⭐ I tool non aggirano niente: il permesso e se il tool scrive si **derivano** dal suo endpoint gemello (`valuta_accesso_endpoint`, `chiamata_in_scrittura`), leggono con la connessione dell'utente (RLS attiva), e ogni lettura — anche l'anteprima di una scrittura — gira in `transazione_sola_lettura`, quindi una scrittura li' dentro la ferma il DB (`25006`). Dettaglio in [brief-db-area-funzionale-assistente-ai](work-done/brief-db-area-funzionale-assistente-ai.md).

Per i building block backend riutilizzabili (helpers, services, repository), consultare il [Catalogo Building Block Backend](backend/catalogo-building-block-backend.md).

---

## Autenticazione e autorizzazione

| Aspetto             | Dettaglio                                                               |
| ------------------- | ----------------------------------------------------------------------- |
| Protocollo          | JWT Bearer su tutti gli endpoint `/api/v1/*`                            |
| Token login         | 3 endpoint namespace-specific (admin/portale/shop), vedi sezione sotto  |
| Token refresh       | 3 endpoint namespace-specific con guard cross-veste                     |
| Dove sta il refresh | ⛔ **Mai nel corpo**: cookie `HttpOnly` (dal 2026-09-28), vedi sotto     |
| Durata access       | 10 minuti; il frontend lo tiene solo in memoria e lo rinnova dal cookie |
| JWT claim custom    | `identita_id` + `ruolo_applicativo` + `sid` (session id stabile)        |
| Permission class    | `ZeroERPPermission` — risoluzione centralizzata                         |
| Superuser           | Bypass totale                                                           |
| SUPER_ADMIN         | Bypass via `script.fn_is_super_admin` (filtro veste OPERATORE, §8.3.7)  |
| Veste spenta        | Nessuna identita' attiva: niente GUC di veste, niente SUPER_ADMIN, il livello d'area nega (dal 2026-10-02 `DISABILITATO` non e' piu' un tipo di veste) |
| Azione processo     | Verificata se la view dichiara `post_permission` / `get_permission`, o letta dalla riga del passaggio (`post_passaggio`) |
| CRUD standard       | Livello area/oggetto (`TUTTO`, `LETTURA`, `BLOCCATO`)                   |
| Scope emittente     | Filtra i dati per emittente fiscale autorizzato (vedi sotto)            |

### Endpoint login/refresh multi-veste (§8.3 PR-B1)

Post refactor multi-face auth, ogni namespace ha i propri endpoint di login
e refresh che ammettono solo il subset di vesti che gli compete:

| Path login                    | Path refresh                          | Vesti ammesse                          |
| ----------------------------- | ------------------------------------- | -------------------------------------- |
| `POST /api/v1/admin/token/`   | `POST /api/v1/admin/token/refresh/`   | `OPERATORE`                            |
| `POST /api/v1/portale/token/` | `POST /api/v1/portale/token/refresh/` | `CLIENTE_PORTALE`, `FORNITORE_PORTALE` |
| `POST /api/v1/shop/token/`    | `POST /api/v1/shop/token/refresh/`    | `SHOP_CUSTOMER`                        |

Il vecchio path unificato `/api/v1/auth/token/` e' stato **rimosso senza
alias** (breaking, grace 0). Client pre-refactor devono aggiornarsi.

⭐ **La chiave d'ingresso e' della porta** (dal 2026-10-06, L-4 del piano
accessi): `admin` vuole `{"username", "password"}`, `portale` e `shop`
`{"email", "password"}` (email senza maiuscole). Il reset password accetta
`{"identificativo"}`, nome utente o email. Dettaglio e sedi:
[api_multi_veste_token.md](../backend/core/manual/api_multi_veste_token.md) §Login.

#### Il login a due passi (secondo fattore, dal 2026-10-01)

Con il secondo fattore **attivo** sulla credenziale, il login risponde 200
**senza** JWT e senza cookie:

```json
{ "two_factor_required": true, "sfida": "<firmata>", "scade_in_secondi": 300 }
```

Il secondo passo è `POST /api/v1/{admin|portale|shop}/token/secondo-fattore/`
con `{"sfida", "codice"}` oppure `{"sfida", "codice_recupero"}`: risponde
nell'envelope `{"data": {"access", "password_change_required"?,
"codici_recupero_rimasti"?}}` e scrive il refresh nel cookie. Sfida scaduta, di
un'altra porta o provenienza → 401 `E_TOTP_SFIDA_NON_VALIDA` (si riparte dalla
password); codice sbagliato → 400 `E_TOTP_CODICE_NON_VALIDO`, e conta come una
password sbagliata. Il successo sul freno si registra solo al secondo passo.
Brief: [sicurezza](work-done/brief-be-fe-sicurezza-header-token-mfa.md) §3.4-bis, T-2.

La configurazione è della persona, su `/api/v1/auth/secondo-fattore/`: `GET` lo
stato, `POST registra/` (QR come data URI di un SVG, segreto e codici di recupero **una volta**),
`conferma/` (`{codice}`), `codici-recupero/` (`{codice}`), `disattiva/`
(`{codice}` o `{codice_recupero}`). Il SUPER_ADMIN, su
`/api/v1/amm-software/credenziali/<id>/secondo-fattore/`: `GET`, `POST obbligo/`
(`{valore}`), `POST disattiva/` (`{motivo}`). Il segno del profilo di reparto è
`richiede_secondo_fattore` nel corpo di `reparti/<uo_id>/profilo/` (assente =
invariato).

⭐ **Gli obblighi della credenziale** (cambio password, configurazione del secondo
fattore) li fa rispettare il cancello dentro `JwtAuditAuthentication`: 403
`E_CAMBIO_PASSWORD_RICHIESTO` / `E_TOTP_CONFIGURAZIONE_RICHIESTA` su ogni view
che non li dichiara in `obblighi_ammessi`. `GET /api/v1/core/me/` li pubblica in
`obblighi_pendenti`, nell'ordine in cui si chiudono: il frontend porta alla
pagina del primo.

Contratto HTTP completo, claim JWT, codici errore e guard cross-namespace:
[api_multi_veste_token.md](../backend/core/manual/api_multi_veste_token.md).

### ⛔ Il refresh token viaggia nel cookie, mai nel corpo

Dal 2026-09-28 ([brief sicurezza](work-done/brief-be-fe-sicurezza-header-token-mfa.md)
§2). Il refresh vale un giorno e rinnova la sessione: in `localStorage` o in un
corpo JSON lo legge qualunque script giri nella pagina. Ora sta in un cookie
che il JavaScript non vede, e l'access (10 minuti) vive solo nella memoria del
frontend.

| Aspetto | Regola |
| --- | --- |
| Cookie | `zeroerp_refresh`, `HttpOnly`, `SameSite=Strict`, `Path=/api/v1/`, `Secure` fuori da DEBUG, durata = `REFRESH_TOKEN_LIFETIME` |
| Chi lo scrive | login (anche il secondo passo, `token/secondo-fattore/`) e refresh dei tre canali, cambio password, cambio emittente attivo: il refresh esce dal corpo e va nel `Set-Cookie` |
| Chi lo legge | refresh, logout, cambio emittente attivo: dal cookie, il corpo non lo porta più |
| Chi lo cancella | il logout, in ogni risposta |
| Anti-CSRF | il refresh è l'unica rotta autenticata dal **solo** cookie, quindi pretende anche `X-Requested-With: XMLHttpRequest` (senza → 403 `E_PERMISSION_DENIED`). Logout e cambio emittente pretendono già il Bearer |
| Sede | ⛔ **un** building block, `apps/core/api/refresh_cookie.py`: nome, attributi, lettura, scrittura e cancellazione. Un cookie scritto con un `Path` e cancellato con un altro non si cancella |

⚠️ `Path=/api/v1/` e non il solo endpoint di refresh: il refresh serve anche a
logout, cambio emittente e cambio password, che stanno altrove (decisione di
Tid, 2026-09-28). Una view nuova che emette o consuma il refresh passa dal BB,
non scrive `set_cookie` a mano.

### Identita utente: `ruolo_applicativo` e `SUPER_ADMIN`

Il vecchio enum `ruolo_sistema` (ADMIN / OPERATIVO / DISABILITATO) e'
stato sostituito dal refactor multi-face auth con:

* `ruolo_applicativo` — categoria dell'identita' digitale
  (`OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`,
  `API_CLIENT`). ⛔ `DISABILITATO` non e' piu' un tipo di veste dal
  2026-10-02 (R-DB-1): una veste spenta tiene il tipo e ha `attivo = false`, e
  la tabella rifiuta il valore (`E_RUOLO_APPLICATIVO_RITIRATO`), che resta
  nell'enum come voce storica. Letto via
  `PermissionResolver.get_ruolo_applicativo(user)` (GUC-first), che risponde
  per la **sessione**: ⛔ mai per un altro utente (S-6). Di un altro si chiede
  il fatto preciso, per esempio `has_veste_operatore_attiva(user)`.
* `SUPER_ADMIN` — privilegio di bypass totale, bindato sulla singola
  identita' via `config.profili_accesso_bindings` (profilo id 9100).
  Letto via `PermissionResolver.is_super_admin(user)`.

⛔ **Nessun punto del backend emette più `ADMIN`/`OPERATIVO`.** Fino al
2026-09-12 questa sezione descriveva una «mapping legacy ricostruita da
`/permessi-effettivi/`» (`SUPER_ADMIN -> "ADMIN"`, altrimenti `"OPERATIVO"`):
non viene ricostruita da nessuno — il vocabolario vecchio è morto in Fase 7 e
il frontend legge `is_super_admin` (analisi-software-per-dati-morti §4).

### Propagazione identita' al DB (GUC)

Al login e su ogni request JWT, `JwtAuditAuthentication` propaga
6 GUC di sessione PostgreSQL per audit e RLS:

| GUC                        | Valore                                                                                 |
| -------------------------- | -------------------------------------------------------------------------------------- |
| `app.jwt_user`             | username Django                                                                        |
| `app.current_user_id`      | `auth_user.id`                                                                         |
| `app.current_identita_id`  | `identita_digitali.id` dell'identita attiva                                            |
| `app.ruolo_applicativo`    | `OPERATORE` / `CLIENTE_PORTALE` / ...                                                  |
| `app.soggetto_ruolo_id`    | `soggetti_ruoli.id` dell'identita'                                                     |
| `app.current_emittente_id` | `emittenti_fiscali.id` dell'emittente in scope (vuoto se il token non ne dichiara uno) |

Invariante "tutto o niente": i 3 GUC di identita' sono popolati insieme
o restano stringa vuota. Vedi
`docs/it/guide/risorse-umane-e-accessi.md` sezione GUC.

**Reset per-richiesta (anti-leak).** `JwtAuditMiddleware.process_request`
azzera i 6 GUC all'**inizio** di ogni richiesta `/api/`, **prima** che
l'auth class li ripopoli e prima di qualunque query. È **incondizionato**
(anche richieste anonime) e **fail-closed**: se il reset fallisce la
richiesta NON viene servita (500 `E_GUC_RESET_FAILED`). Chiude il leak
cross-request sulle connessioni persistenti (`CONN_MAX_AGE > 0` / pooling),
critico ora che la RLS filtra in base ai GUC. Vedi
`docs/it/dev/work-done/analisi-attivazione-rls-operatori-be-fe.md` §1.

**L'audit lo scrive il DB, non il repository.** Sulle tabelle che montano
`script.trgfn_audit_data_user_generic` (lo dice la scheda auto-generata
della tabella, sezione trigger) il trigger scrive, dal GUC `app.jwt_user`,
`user_insert` sull'INSERT e `data_update`/`user_update` a ogni INSERT e
UPDATE, e **sovrascrive** quello che passa il BE.

* ⛔ Un INSERT non nomina `user_insert`; un UPDATE (o il ramo `DO UPDATE`
  di un upsert) non nomina `data_update` né `user_update` — nemmeno come
  `extra_set` di `execute_dynamic_update`, né come `user_update =
  CURRENT_USER`. Riscriverli è la stessa regola su due livelli: oggi
  innocua perché il trigger vince, domani falsa per chi la legge.
* Le colonne dell'audit **si leggono** (SELECT, tipi, liste), non si
  scrivono.
* ⚠️ La regola vale **solo** dove il trigger c'è. Le preferenze utente
  (`ui.lista_preferenza_utente`, `ui.dashboard_preferenza_utente`) hanno
  `data_update` senza `user_update` e senza trigger: lì il repository la
  scrive, ed è giusto.
* ⚠️ Una data con un **significato di dominio** non è l'audit e ha una
  colonna sua (per esempio `contenuto_aggiornato_il` dei preset, scritta
  dai trigger a mano del DB): non si ricava da `data_update`.

Censimento e ritiro: BE11 di `brief-db-revisione-dbops` (2026-11-08).

### Scope emittente

Due pattern disponibili in base al dominio:

1. **Vendite** — `get_scope_user_id(request)` passa `auth_user_id` alle funzioni SQL
   che risolvono lo scope internamente via `fn_get_emittenti_scope_sr_ids`.
2. **Search / Anagrafiche** — `PermissionResolver.get_emittenti_sr_ids(request.user)`
   risolve in Python i `soggetto_ruolo_id` degli emittenti autorizzati e li passa
   come array `bigint[]` alle query SQL.

⛔ **Perimetro ≠ attore.** `get_scope_user_id` vale `None` per il superuser perché
il suo perimetro non ha limiti: serve **solo alle letture**. Una scrittura che
passa l'utente a un gate (prezzi L1/L2/L3), all'audit o a una pratica usa
`get_actor_user_id(request)`: con lo scope, il gate legge il `None` del superuser
come «chiamata senza utente» e lo blocca.

Usare `get_emittenti_sr_ids` (filtra su `*_soggetto_ruolo_id`, convenzione SR)
o `get_emittenti_pk_ids` (filtra su `emittente_fiscale_id` PK) secondo la colonna.
⛔ Sono i **soli due nomi**: l'alias `get_emittenti_ids` — dichiarato deprecato
dal 2026-05-02 e arrivato a **nove** chiamanti, più dell'originale — è stato
tolto il 2026-09-12 (analisi-software-per-dati-morti §2.7). *Un nome deprecato
che non cala è un nome in servizio*; il presidio è il grep a zero.

**Enforcement RLS (operatori) — dal 2026-06.** Lo scope emittente degli OPERATORI
è applicato **anche a livello DB** via Row Level Security sulle tabelle sensibili
(`vendite.fatture` / `fatture_scadenze` / `fatturazione_lotti` / `ordini` /
`preventivi` / `contratti` / `offerte_commerciali`, `documenti.documenti_generati`,
`pratiche.pratiche`, `anagrafiche.billing_account`). I filtri applicativi
(`get_emittenti_*`) **restano** come defense-in-depth e si sommano. Conseguenze per
il consumer API:

* le **liste** restituiscono solo le righe degli emittenti in whitelist
  dell'operatore (filtro automatico, anche dove il filtro applicativo non c'era);
* un **dettaglio by-id** di un record fuori scope torna **404** (`E_*_NOT_FOUND`),
  identico a un id inesistente — il FE lo gestisce come "non trovato/non accessibile"
  (composable `useDrawerDetailLoad`: toast + chiusura drawer);
* una connessione **senza GUC** vede **0 righe** (fail-closed); i ruoli tecnici
  `BYPASSRLS` (migrazioni, job batch owner) restano esenti.

⭐ **E dal 2026-09-10 il perimetro arriva fino ai satelliti.** Righe, componenti,
indirizzi, riepiloghi IVA, note, log, gruppi di lotto, link delle pratiche —
ogni tabella figlia di una testata protetta porta la **propria** policy
(`script.fn_scope_ef_whitelist_via_<testata>`: lo stesso `EXISTS` sulla
testata, un `JOIN` diverso per famiglia), e un presidio a criterio transitivo
(`dbops.vw_rls_perimetro_scoperto` + `dbops.rls_perimetro_debito`, pgTAP
`rls/test-rls-perimetro-scoperto.sql`) fa rosso su una tabella nuova con una FK
verso una protetta e nessuna policy. Il cantiere è il **D2 del gemello DB**
(`work-in-progress/migliorie-generali-da-test-valutazione.md`, D2 chiuso l'11-09): changeSet
`20260909-27` ÷ `20260910-33`, undici famiglie — `fatture` e le sue righe
erano protette già dal `20260729-05`, le partizioni di `vendite.note` dal
`20260909-71/72`.
⚠️ **Conseguenza per chi scrive un endpoint**: la regola *«leggi prima la
testata»* resta l'**ordine** giusto — fuori scope si risponde 404, non un
pannello vuoto, e il conteggio non deve dire «12» mostrandone 3 — ma non è più
l'**unico** cancello: leggere un satellite da solo non è più fail-open. ⛔ Fino
a quel giorno cinque voci dell'inventario qui sopra dicevano «la testata ha la
RLS, il figlio no»: corrette il 2026-09-12, e il fatto sta scritto **qui** e
non più in cinque sedi.

⭐ **E l'ordine si scrive con un BB, non a mano** (2026-09-21):
`testata_o_not_found(getter, id, code=…, message=…, id_name=…, function_name=…)`
in `apps/core/services/testata_guard.py`. Ogni service di documento lo avvolge
nel proprio `_get_testata_or_raise(repo, id, *, op)` — nome uguale in ordini,
DDT, preventivi e resi — e i satelliti (`list_righe`, `list_riepilogo_iva`,
`list_revisioni`, `list_componenti_riga`) lo chiamano **prima** del repository.
Per una **riga** nell'URL il gemello e' `riga_del_padre_o_not_found` (via
`_get_riga_or_raise(repo, <doc>_id, riga_id, *, op)`): esiste **ed** e' di quel
documento, o 404 — `/ordini/999/righe/24/` non apre la riga 24 di un altro ordine.
⚠️ Il censimento di quel giorno aveva trovato **dieci** satelliti di `vendite`
che passavano dritti al repository: sotto RLS rispondevano `200 []` a un padre
fuori perimetro, indistinguibile da «nessuna riga». Un satellite nuovo che
non legge la testata è lo stesso difetto, e non dà nessun errore.
⭐ **E un pre-check Python di una regola che il DB fa rispettare usa il codice del DB**
(2026-09-22, decisione B di Tid): «le righe si toccano solo in bozza» è
`E_RIGA_DOC_NON_BOZZA` sia dal trigger `trgfn_doc_righe_lock_fuori_bozza` sia dai
pre-check di ordini/DDT/preventivi/contratti/resi (BB `richiedi_righe_in_bozza`,
frase a catalogo composta coi tre valori). Prima erano **cinque** codici
(`E_DDT_STATO_TRANSIZIONE`, `E_ORD_STATO_TRANSIZIONE`,
`E_PREV_STATO_NON_MODIFICABILE`, `E_CONTRATTO_NON_MODIFICABILE`,
`E_RESO_STATO_TRANSIZIONE` — che restano alla **testata**; `E_CONTRATTO_NON_MODIFICABILE`
è ritirato dal 2026-10-11: la regola la dice il lock dei satelliti, `E_DOC_DATI_COLLEGATI_NON_BOZZA`), cioè lo stesso
rifiuto con due nomi a seconda di chi lo diceva. Il pre-check è lecito — un 409 prima di
scrivere, e l'unico cancello dove il DB non arriva ancora — ma la regola è **una**
e ha un nome a catalogo: chiunque la sollevi la chiama così.

⛔ **Il doppio filtro Python su OGNI endpoint non è la regola** — è esattamente
il pattern che l'analisi RLS (§2.3) ha dichiarato fragile: la RLS è il
cancello uniforme, il filtro applicativo sta sulle **liste di testata** (tutte
quelle di `vendite` e `anagrafiche`, offerte comprese dal 21-09) e l'ordine di
lettura sui satelliti. `pratiche` resta da allineare: brief
`work-in-progress/brief-be-pratiche-perimetro-emittente-lato-python.md`.

Vedi `docs/it/dev/work-done/analisi-attivazione-rls-operatori.md`.

---

## Decisioni architetturali

### Validazione input

La validazione vive nel **service layer**, col building block `PayloadValidator`
(`apps/core/services/payload_helpers.py`), istanziato una volta per service col
codice d'errore del dominio:

```python
_V = PayloadValidator(validation_code="E_DDT_VALIDAZIONE")

# il contratto: una chiave fuori whitelist e' un 400, prima di qualunque lettura
data = _V.solo_chiavi_ammesse(payload, ammesse=CREATE_PAYLOAD_RIGA, colonne=CREATE_KEYS_RIGA,
                              function_name=f"{_FN}.gestisci_riga")
quantita = _V.require_decimal(payload, "quantita", min_value=Decimal("0"))
tipo = _V.optional_enum(payload, "tipo", allowed=TIPI_AMMESSI)
```

* Un metodo per tipo (`require_*` / `optional_*` / `extract_optional_*` a tre stati
  per i PATCH): stringhe, interi, decimali (rifiuta `NaN`), enum, date, uuid, booleani.
  L'elenco e le regole stanno nel
  [catalogo BB backend](backend/catalogo-building-block-backend.md) (`PayloadValidator`).
* ⛔ **Un flag del corpo non si legge con `bool(payload.get(...))`**: `bool("false")` è
  `True` (il 2026-10-20 creava un SUPER_ADMIN). Si usa `optional_bool` / `require_bool`.
* ⛔ Niente helper locali `_require_str`, `_extract_*` nei service: sono le copie che il
  BB ha ritirato. Quelle che restano sono debito, non modello.
* Non si usano serializer DRF né Pydantic per **validare**. I serializer compaiono solo
  come descrizione dello schema OpenAPI, e quello del corpo si **legge dal contratto**
  (`schema_da_contratto`, §Checklist nuovo endpoint), non si scrive a mano.

### Comunicazione cross-modulo

I service possono chiamare direttamente service/repository di **anelli interni**
(es. anagrafiche chiama core). NON sono ammesse chiamate laterali tra moduli
allo stesso livello (es. vendite non chiama pratiche direttamente).

Quando servira' comunicazione laterale, introdurre un dispatcher sincrono interno.
Non prima.

### Letture vs scritture

Separazione logica, non fisica. Nei repository:

* **Letture**: SQL diretto su view PostgreSQL, ottimizzate per proiezioni
* **Scritture**: stored functions PostgreSQL, transazionali con trigger

Non creare sottodirectory `commands/` e `queries/`. La separazione
nei commenti e nelle sezioni del file e' sufficiente.

#### ⛔ Una GET non scrive, e lo garantisce il DB

Dal 2026-09-25 ogni `GET`/`HEAD` delle API gira in una transazione di **sola
lettura** (`SolaLetturaMiddleware`, ultimo della catena; il blocco e' il BB
`transazione_sola_lettura`). Una scrittura tentata dalla view — anche dentro una
funzione `SECURITY DEFINER` — fallisce, e arriva come **500
`E_SCRITTURA_IN_LETTURA`** col nome della view nel log. Conseguenze per chi
scrive codice:

* un service chiamato da una `GET` non scrive **sulla connessione della
  richiesta**: se deve farlo, la scrittura esce dalla `GET` (un'azione `POST`),
  oppure la view lo **dichiara** con `scrittura_in_get = "<motivo>"`, e il
  presidio `test_sola_lettura_rotte` la elenca per nome. Il motivo si scrive;
  una dichiarazione senza motivo non vale;
* niente `SELECT ... FOR UPDATE` in una `GET`: in sola lettura PostgreSQL lo
  rifiuta;
* niente `transazione_sola_lettura` dentro una `GET`: c'e' gia', e il BB
  rifiuta di partire dentro una transazione aperta;
* le GUC (`set_config`), il `tx_id` e il diario degli errori funzionano: non
  sono scritture sulla connessione della richiesta.

Contratto completo: [sola_lettura_middleware](../backend/core/manual/sola_lettura_middleware.md).

### Atomicità e composizione di scritture

Un endpoint che modifica stato è **un'unità di lavoro atomica**. Quando l'operazione compone
**più scritture** (INSERT/UPDATE o `SELECT fn_...` di mutazione), decidere **dove** vive la
transazione — non lasciarle in autocommit una dietro l'altra (se la 2ª fallisce, la 1ª resta
committata → stato parziale / orfani).

| L'operazione...                                                           | Meccanismo                                                                                         |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| compone **solo** scritture/fn DB                                          | **una sola `SELECT fn_madre(...)`** nel repository — atomica per costruzione (preferito, DB-first) |
| richiede orchestrazione **Python** (lock, dispatch handler, control-flow) | **`with transaction.atomic()`** esplicito nel service                                              |
| ha un **side-effect esterno** (email/SMTP)                                | pattern **outbox/saga**, mai dentro la transazione                                                 |

> ⚠️ **Non affidarsi a `ATOMIC_REQUESTS`.** Sarebbe inefficace qui: `handle_post_json` **cattura**
> l'eccezione e restituisce una `Response`, quindi non esce mai dalla view → il rollback a livello
> di request non scatta e il parziale viene committato (e su `IntegrityError` il 4xx diventa 500).
> **`with transaction.atomic()` esplicito è invece sicuro**: fa rollback al confine del blocco (nel
> suo `__exit__`), *prima* che `handle_post_json` catturi l'eccezione. È l'attrezzo corretto.

**Guardrail: «una azione = una unità atomica».** Un metodo service che compone 2+ scritture con
side-effect **deve** avvolgerle in un solo `transaction.atomic()` **oppure** delegare a una singola
funzione madre DB. Domini con natura mista (es. pratiche): le operazioni pure-dato → madre DB
(`pratiche.fn_crea_pratica`); il motore-flussi-con-handler → `transaction.atomic()`.

**Enforcement CI.** Un test AST — `apps/core/tests/test_transaction_atomicity_guardrail.py` (gira
senza DB) — fallisce se un metodo compone 2+ scritture non tutte in un `transaction.atomic()`.
Copertura **v1 = livello repository** (`cursor.execute` di scrittura, con `ALLOWLIST` motivata per i
casi deliberati — vuota dal 2026-10-24, quando la prenotazione idempotency è passata a
`dbops.fn_idempotency_prenota`); il livello service (2+ chiamate a metodi-write del
repo) è un **follow-up v2** (richiede euristiche receiver-aware per non generare falsi positivi). La
regola sopra vale comunque per intero: il check automatico ne presidia oggi il sottoinsieme più
verificabile, non sostituisce la disciplina in review.

> Faccia DB della stessa regola (come scrivere la funzione madre): [linee-guida-sql §5b](/linee-guida-sql).
> Caso di studio, criterio esteso e catalogo dei finding:
> [analisi-fix-transazioni](/dev/work-done/analisi-fix-transazioni).

### Tassonomia errori

Tutti i codici errore seguono `E_{MODULO}_{TIPO}` e DEVONO essere registrati
prima dell'uso. Il suffisso **suggerisce** la categoria:

| Suffisso                        | HTTP tipico | Esempio               |
| ------------------------------- | ----------- | --------------------- |
| `_VALIDATION` / `_VALIDAZIONE`  | 400         | `E_ANAG_VALIDAZIONE`  |
| `_NOT_FOUND`                    | 404         | `E_PRATICA_NOT_FOUND` |
| `_DUPLICATO` / `_IN_ESECUZIONE` | 409         | `E_ANAG_DUPLICATO`    |
| `_NEGATO` / `_DENIED`           | 403         | `E_PERMESSO_NEGATO`   |

#### ⭐ Registrare un codice = dargli una **classe** (dal 2026-08-07)

⚠️ **Non si scrive più lo status.** Fino al 2026-08-07 registrare un codice
voleva dire aggiungere una riga con `http_status`, `ui_action` e messaggio a un
dizionario di 659 voci. Ora si dichiara **che cosa è** l'errore — la sua
`classe` — e status e `ui_action` si **derivano**.

| classe            | HTTP        | Quando                                                               |
| ----------------- | ----------- | -------------------------------------------------------------------- |
| `DATO_ERRATO`     | 400         | la richiesta è malformata o il valore è sbagliato                    |
| `CONFLITTO_STATO` | 409         | in conflitto con lo stato attuale della risorsa                      |
| `NON_TROVATO`     | 404         | la cosa indicata non esiste                                          |
| `TECNICO`         | 500         | guasto o pezzo non configurato: l'operatore non può farci niente     |
| `NON_PERMESSO`    | 403         | il diritto manca, e non dipende dallo stato                          |
| `NON_ESEGUIBILE`  | 422         | si capisce ma non si può eseguire                                    |
| `NON_DISPONIBILE` | 501         | funzione presente ma non servita (disattivata)                       |
| `NON_AUTENTICATO` | 401         | non autenticato (≠ 403: autenticato ma senza diritto)                |
| `ERRORE_ESTERNO`  | 502         | un provider esterno ha risposto male                                 |
| `AVVISO`          | **nessuno** | non è un rifiuto: si scrive nel diario e non raggiunge mai il client |

Il vocabolario è lo stesso di `config.classi_errore`. **La mappa classe → HTTP
resta lato backend**, ed è una scelta: è *trasporto*, non dominio — il database
non deve sapere cosa sia un 409.

⭐ **Le classi erano otto fino al 2026-08-07, e le due arrivate dopo dicono
qualcosa.** 401 e 502 erano dichiarati «fuori dal vocabolario di dominio, da
mappare a mano nel backend». Non lo erano: sono righe del catalogo come tutte le
altre, quindi con `classe NOT NULL` una classe la vogliono. Con
`NON_AUTENTICATO` ed `ERRORE_ESTERNO` a vocabolario **l'eccezione dei cinque
codici sparisce**: non c'è più nessuna mappa per codice nel backend, si deriva
tutto dalla classe — e il prossimo codice di autenticazione prenderà il suo 401
senza che nessuno lo scriva.

**Dove si mette cosa** — quattro moduli in `apps/core/services/`, separati per
**quando cambiano** e non per contenuto:

| Modulo                        | Cosa                                                      | Chi lo scrive                                        |
| ----------------------------- | --------------------------------------------------------- | ---------------------------------------------------- |
| `error_policies_generated.py` | `codice → classe`, una voce per codice del catalogo, ritirati compresi (`CODICI_RITIRATI`) | ⛔ **GENERATO** da `config.vw_codici_errore_identita` |
| `error_policies.py`           | `classe → (status, ui_action)` — 10 righe + la logica     | a mano, quasi mai                                    |
| `error_ui_overrides.py`       | le `ui_action` fuori default, **coi loro perché**         | a mano, quando cambia una scelta di UI               |
| `error_messages_fallback.py`  | i messaggi **senza segnaposto**                           | a mano, per ora                                      |

I numeri li dice il codice (`len(CLASSE_PER_CODICE)`, `len(UI_ACTION_OVERRIDE)`), non
questa pagina. Fatto datato 2026-10-25: 1135 voci (122 ritirate), 156 override.

⛔ **Il primo modulo non si modifica a mano.** Per dare una classe a un codice si
cambia il **catalogo** e si rigenera:

```bash
# 1. il team DB semina il codice in codici_errore.csv con la sua classe
# 2. lato backend:
./manage-env.sh genera_error_policies          # riscrive il modulo
./manage-env.sh genera_error_policies --check   # non scrive: dice se diverge
```

Il `--check` è quello che gira in CI (come test, `test_error_policies_divergenza_db`):
un file generato che nessuno rigenera torna a essere scritto a mano senza che
nessuno lo decida.

⚠️ **I codici ritirati restano nel modulo e continuano a risolvere**, perché
`dbops.error_log` contiene le loro righe e devono restare leggibili —
`obsoleto_dal` non è `attivo = false`. Ma **nessun punto di chiamata nuovo deve
nominarli**: lo presidia `test_error_codes_declared_guardrail`, e per la stessa
ragione `ErrorPolicyRegistry.has()` oggi risponde *«lo conosco»*, non *«è
buono»*. La domanda «questo codice si può usare?» si fa su `CODICI_RITIRATI`.

#### ⛔ Il rubinetto degli accumulatori: riusare un codice per una condizione nuova

`scripts/codici-errore-baseline.sh` (CI) confronta, per ogni codice, **le
famiglie di condizione** su cui viene sollevato — lette dalla riga di guardia in
`pg_proc`:

| guardia                        | famiglia                                           |
| ------------------------------ | -------------------------------------------------- |
| `EXCEPTION WHEN …`             | `ECCEZIONE`                                        |
| `IF NOT FOUND`                 | `NOT_FOUND`                                        |
| `IS NULL` / `<= 0` su un `p_*` | `PARAMETRO`                                        |
| `NOT IN (…)`                   | `ENUM`                                             |
| `x <> 'LETTERALE'`             | `VALORE_ATTESO` — dal 2026-09-07                   |
| tutto il resto                 | `IGNOTO` — la misura dichiara di non saper leggere |

⚠️ **L'ordine conta**: un `NOT IN` resta `ENUM`, e una guardia su un parametro
nullo resta `PARAMETRO` anche se confronta un letterale.

Un codice che **acquista una famiglia che non aveva** ferma la CI.

> ⭐ **Non è pedanteria: è il modo in cui gli accumulatori si formano davvero.**
> Nessuno crea un codice generico di proposito. Si prende quello che c'è già e lo
> si usa «anche per questo caso qui», una volta sola, e sembra ragionevole. La
> sessantottesima volta è `E_GENERICO`.

⛔ **La baseline non si aggiorna per far passare la CI.** Il rosso è la richiesta
di una decisione, e le uscite sono due: o il codice nuovo va creato, o l'uso è
legittimo e allora la baseline si aggiorna **con la ragione nel messaggio di
commit**.

**Il caso vero, 2026-09-06.** `config.fn_chiudi_email_sistema` sollevava
`E_VALIDAZIONE` su tre condizioni diverse, e una era `IF NOT FOUND` — «nessuna
email con questo identificativo». ⇒ La CI si è fermata.

La decisione non è stata aggiornare la baseline: `E_VALIDAZIONE` è di classe
`DATO_ERRATO`, cioè *«hai sbagliato i dati»*, ma quell'identificativo **non
arriva mai da una persona** — è l'id che il backend ha scritto un istante prima.
⇒ Codice nuovo, `E_EMAIL_LOG_INESISTENTE`, classe **`TECNICO`**.

⚠️ **E non `NON_TROVATO`**, che sarebbe stata la scelta d'istinto: quella classe
porta un **404**, giusto quando è una *persona* a chiedere una cosa che non c'è.
Qui chi chiede è il backend, e un 404 manderebbe a cercare una risorsa mancante
invece di un difetto di codice. ⇒ **La famiglia della condizione non decide la
classe**: la prima dice *com'è fatta la guardia*, la seconda *chi ha sbagliato*.

⚠️ **Un codice nuovo vuole anche il suo ripiego.** `error_messages_fallback.py`
deve avere una frase **senza segnaposto** per ogni codice vivo — lo presidia
`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`. Senza, l'operatore vede una
frase neutra che non parla del suo problema.

##### ⭐ Il seguito, 2026-09-07: quando cambia il **metro** e non il misurato

Il giorno dopo, un changeSet ha insegnato al classificatore una quinta famiglia —
**`VALORE_ATTESO`**, cioè `x <> 'LETTERALE'`: la forma di ogni guardia di *stato*
o di *perimetro*, che prima cadeva tutta in `IGNOTO`. ⇒ Il rubinetto si è fermato
su **otto** codici in una volta.

⛔ **Sette non erano accumuli, e l'ha detto il conteggio**: per tutti e sette i
*punti di sollevamento* erano identici alla baseline. Nessuno aveva allargato
niente — era il metro a essere cambiato sotto. ⇒ Ri-base, con la ragione nel
commit.

⭐ **L'ottavo sì, ed è il caso che vale.** `E_VALIDAZIONE` guadagnava un punto
sulla **terza** guardia della stessa `fn_chiudi_email_sistema`: *«la riga esiste
ma non è di ambito SISTEMA»*. Non è un dato sbagliato — è la **porta sbagliata**,
e `E_VALIDAZIONE` è `DATO_ERRATO`. ⇒ Codice nuovo,
`E_EMAIL_LOG_NON_DI_SISTEMA`, **`TECNICO`** — la stessa decisione del giorno
prima, sulla guardia accanto.

> ⚠️ **La lezione operativa, e serve la prossima volta che nasce una famiglia.**
> Una famiglia nuova produce **due** effetti che si assomigliano e vanno separati
> uno per uno: cambia il metro su chi già usava quel codice, e **rende visibile**
> ciò che prima era illeggibile. ⛔ Il primo si ri-basa, il secondo **no**: è una
> segnalazione vera arrivata in ritardo. Il discriminante è il **conteggio dei
> punti** — se non si muove, non ha allargato nessuno.
>
> ⭐ E ri-basare l'ottavo avrebbe dichiarato `VALORE_ATTESO` **ammessa** su un
> codice `DATO_ERRATO`: la baseline sarebbe marcita nel **verso permissivo**,
> l'unico in cui un presidio marcisce senza che nessuno se ne accorga.

⚠️ **Che quella guardia fosse sbagliata era già scritto**, nel changeSet del
giorno prima: *«la stessa regola direbbe di spezzare ancora […] la lascio perché
il classificatore non l'ha segnalata — ma è una domanda aperta, non una svista»*.
⇒ **Un dubbio dichiarato e non risolto vive finché uno strumento non lo trova.**
Vale la pena scriverlo lo stesso: è ciò che ha reso la segnalazione leggibile in
un minuto invece che in un'indagine.

Storia completa: `docs/it/dev/work-done/brief-db-sveglia-dei-processi.md` §23.

⚠️ **`ui_action` non si deriva dalla classe, e il numero conta.** Gli override
stanno per lo più sulla classe **`DATO_ERRATO`** (al 2026-10-25: 99 su 156): lì il
default è un lancio di moneta, perché il discriminante non è la classe ma
**dove manca il dato**, sul form in corso (`highlight_form_fields`) o
sull'entità collegata (`show_error_banner`). Il default scelto è il banner:
promettere un campo da evidenziare che non esiste è peggio del contrario.

⚠️ **Una classe senza status mappato solleva `ClasseErroreSenzaStatus`**, non
ripiega. È la garanzia per `AVVISO`: prima `resolve()` non falliva mai e un
avviso sfuggito al cancello sarebbe diventato un **500 col messaggio soppresso**.

**Quattro codici di autenticazione** (`E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA`,
`E_AUTHENTICATION_FAILED`, `E_NOT_AUTHENTICATED`) prendono il 401 dalla **propria
eccezione DRF** (`status_code` delle sottoclassi di `AuthenticationFailed`, letto da
`drf_exception_handler`), non dalla policy: la classe `NON_AUTENTICATO` dà loro
messaggio e `ui_action`. `E_AI_PROVIDER_ERROR` oggi non raggiunge il client: l'errore
del provider finisce nel log delle domande all'assistente (`dbops.ai_query_log`) e
l'utente riceve una risposta di cortesia.

> Perché tutto questo: `docs/it/dev/work-done/brief-db-be-classe-codici-errore.md`.
> In una riga: il significato di un errore viveva **solo** in un dizionario
> Python, quindi il catalogo DB non aveva il campo dove la contraddizione si
> sarebbe vista.

#### ⚠️ Il suffisso NON decide lo status: decide il punto che solleva

La tabella sopra è una **convenzione di naming**, non una regola di mapping. Usarla
per assegnare uno status è il modo più rapido di sbagliare, e non è un'ipotesi:
assegnando 91 policy in un giorno (2026-08-06) **il nome ha mentito tre volte**.

| Codice                    | Cosa suggerisce il nome | Cosa fa davvero il punto che solleva                                                                 | Status  |
| ------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------- | ------- |
| `E_SNAPSHOT_ID_NOT_FOUND` | 404                     | `EXCEPTION WHEN OTHERS` nella storicizzazione: non manca un record, fallisce la lettura della chiave | **500** |
| `E_DELETE_NOT_ALLOWED`    | 409 (stato sfavorevole) | blocca **sempre**, sbloccabile solo da una GUC di sistema: è un diritto che manca                    | **403** |
| `E_FULFILL_NOT_FOUND`     | «manca un legame»       | la riga indicata non esiste (`SELECT INTO` → NULL)                                                   | **404** |

E in senso opposto: `E_PARAMETRO_INVALIDO` viene sollevato in due punti su un
`IF NOT FOUND`, dove la verità è 404 — ma **non si corregge cambiando la sua
policy**: 113 funzioni lo nominano e per 111 il 400 è giusto. Un codice usato per
due cose si spezza a monte, non si rimappa a valle.

> **Regola operativa: leggere la funzione che solleva, non il nome del codice.**
> Se il codice è sollevato da più punti con verità diverse, lo status giusto è il
> **denominatore sicuro** (quello che non fa danno in nessuno dei punti), e il
> codice va segnalato al team DB come candidato allo split.

**Due corollari, pagati entrambi sul campo** (2026-08-07):

* ⚠️ **conta il ramo, non la funzione.** Due `IF` adiacenti nella stessa funzione
  possono avere verità opposte: in `dbops.fn_accoda_lavoro`,
  `E_JOB_TYPE_NON_TROVATO` è **500** (tipo mai registrato: difetto di deploy) e
  `E_JOB_TYPE_NON_ATTIVO` è **501** (tipo esistente, disattivato di proposito).
  In `fn_push_offerta_a_contratto` due guardie quasi identiche hanno richiesto
  codici diversi, e la prima misura le aveva confuse;
* ⚠️ **se la funzione ha gemelle per dominio, il perimetro sono tutte.**
  `fn_contratto_riga_componenti_init` ha tre gemelle (`ddt`, `ordine`,
  `preventivo`): lo stesso difetto stava in tutte e quattro, ma è stato corretto
  su una sola e le altre tre sono tornate al giro dopo. Nello stesso file, nello
  stesso giorno, un altro difetto era già stato trattato **come famiglia**.

⚠️ **Non introdurre codici generici nuovi.** Un codice che serve a due punti
diversi è due codici. `E_PARAMETRO_INVALIDO` è nominato da **177 punti** ed
`E_VALIDAZIONE` da **13**: nessuno dei due è stato scelto per mancanza di
alternative, erano **generici e a portata di mano**, e in un caso il commento nel
DB confessa di aver scelto il codice per il numero di `%s` del messaggio.

> ⭐ **Ma «generico» e «accumulatore» non sono la stessa cosa, e questo documento
> lo diceva sbagliato fino al 2026-08-07.** Diceva che i due erano *«la prova di
> dove si finisce»*, contando le **funzioni** che li nominano — 113 e 10, «cinque
> domini». Contate invece le **condizioni** che li sollevano (team DB, eseguendo
> lo split che questa misura aveva reso urgente):
>
> | Codice | Punti | Guard di parametro (`IS NULL OR <= 0` e simili) | Altro |
> |---|---:|---:|---:|
> | `E_VALIDAZIONE` | 13 | **13** | **0** |
> | `E_PARAMETRO_INVALIDO` | 177 | 160 (90%) | 17 |
>
> `E_VALIDAZIONE` **non è un accumulatore**: tutti e 13 i punti sono la guard di
> parametro che [AGENTS.md](../../../.codex/AGENTS.md) prescrive. Lo split
> programmato è stato chiuso **senza fare niente**. Il caso che sembrava
> dimostrare il contrario — *«`fn_annulla_reso` che rifiuta un annullamento è un
> conflitto di stato»* — non esiste: lì `E_VALIDAZIONE` scatta su
> `p_reso_id IS NULL OR p_reso_id <= 0`, e non rifiuta nessun annullamento.
>
> **La regola che ne esce, e vale oltre questi due:** *un codice è un
> accumulatore quando copre **condizioni** diverse, non quando è usato in
> **domini** diversi.* «10 funzioni, 5 domini» era un numero vero che misurava la
> cosa sbagliata — le funzioni erano eterogenee, la condizione no. Prima di
> proporre uno split, contare le condizioni ai punti che sollevano.

**Quando spezzare un codice e quando no.** Un codice a più significati si spezza
quando i significati **portano a reazioni diverse della pagina**, non perché sono
più d'uno: `E_STATO_SCONOSCIUTO` diceva «stato di workflow inesistente» (404, la
pagina torna indietro) e «nazione dell'indirizzo non risolta» (400, si evidenzia
il campo) — reazioni opposte, spezzato. `E_SOGGETTI_RUOLI` ne copre tre, ma tutte
e tre chiedono un 400: tenuto insieme, con la ragione scritta nella policy.

#### Gli status in uso, tutti — e cosa è standard e cosa è nostro

⚠️ **Gli status HTTP non li abbiamo inventati noi.** Sono uno standard IETF:
**RFC 9110 «HTTP Semantics»** (giugno 2022, che ha sostituito RFC 7231/7235), e
il registro ufficiale dei codici è quello IANA. Quando questo documento dice
«404 = non esiste» sta citando lo standard, non una convenzione di progetto.

**Nostro** è invece tutto il resto, e conviene sapere dove passa il confine:

| Cosa                                   | Chi lo stabilisce                   |
| -------------------------------------- | ----------------------------------- |
| il significato di 400/403/404/409/500… | **RFC 9110** (standard)             |
| il nome dei codici (`E_MODULO_TIPO`)   | noi                                 |
| quale codice mappa su quale status     | **noi** — è la decisione di dominio |
| il vocabolario `ui_action`             | noi, non esiste nulla di standard   |

Censimento del dizionario al 2026-08-07, a registro del debito azzerato
(**659 policy**):

| Status                        | Quanti | Fonte             | Quando                                                                                                                                                              |
| ----------------------------- | ------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **400** Bad Request           | 234    | RFC 9110          | la richiesta è malformata o il valore è sbagliato                                                                                                                   |
| **409** Conflict              | 224    | RFC 9110          | «conflitto con lo stato attuale della risorsa» — la definizione dello standard è **letteralmente** il nostro caso: transizioni non ammesse, immutabilità, duplicati |
| **404** Not Found             | 84     | RFC 9110          | la cosa indicata non esiste                                                                                                                                         |
| **500**                       | 63     | RFC 9110          | anomalia tecnica: l'operatore non può farci niente                                                                                                                  |
| **403** Forbidden             | 23     | RFC 9110          | il diritto manca, e non dipende dallo stato                                                                                                                         |
| **422** Unprocessable Content | 22     | RFC 9110 §15.5.21 | sintassi valida, **semantica** no: il payload si capisce ma non si può eseguire                                                                                     |
| **401** Unauthorized          | 4      | RFC 9110          | non autenticato (≠ 403: autenticato ma senza diritto)                                                                                                               |
| **501** Not Implemented       | 4      | RFC 9110          | funzione non implementata / disattivata                                                                                                                             |
| **502** Bad Gateway           | 1      | RFC 9110          | un provider esterno ha risposto male                                                                                                                                |

**Tutti e nove vengono da RFC 9110**: dopo l'audit non resta in uso nessuno
status fuori dal nucleo HTTP.

> ⚠️ **Se si rifà questo censimento**, contare i blocchi delimitando ogni voce
> con la **chiave successiva**, non con un terminatore di indentazione: la prima
> versione di questa tabella si fermava a 570 policy su 602 perché l'ultima riga
> di un blocco non è sempre indentata allo stesso modo, e il conteggio risultava
> plausibile ma sbagliato. *Anche la misura è un programma, e può avere il suo
> difetto.*

**Audit di coerenza del 2026-08-06** — cercando famiglie che rispondono in due
modi, su 601 policy è emersa **una sola divergenza vera**:
`EMITTENTE_NON_MODIFICABILE` (409) contro `E_EMITTENTE_NON_MODIFICABILE` (400),
unica fra le **53** coppie legacy/prefissato. La voce senza prefisso era orfana —
il team DB aveva già tolto quel codice dal catalogo — ed è stata rimossa; i tre
codici della famiglia «immutabilità» che stavano a 400 sono passati a **409**,
allineandosi agli altri 29. `ui_action` invariata: a video non cambia nulla,
cambia il contratto.

**I tre status con un solo uso, esaminati uno per uno** (2026-08-06). «Usato una
volta sola» non è di per sé un difetto: il difetto è usare uno status per una
cosa che lo standard non dice. Esito diverso per tutti e tre:

| Era                           | Codice                       | Esito                                                                                                                                                                                                                                                                                                                         |
| ----------------------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **423** Locked                | `E_UTENTE_BLOCCATO`          | → **403**. Il 423 di RFC 4918 è il lock WebDAV di una **risorsa**, non di un account; il gemello `E_USER_DISABILITATO` è già 403. ⚠️ E **non** 429, che sembrerebbe ovvio: `LoginView.resolveLoginError` intercetta il 429 **prima** di leggere il codice (throttle per IP) e il messaggio coi minuti rimanenti andrebbe perso |
| **428** Precondition Required | `E_AI_CONFIRMATION_REQUIRED` | **ritirato**. Non lo sollevava nessuno: il flusso di conferma dei tool in scrittura restituisce **200 con `requires_confirmation` nel payload** — una conferma richiesta non è un errore HTTP. E il 428 (RFC 6585) significa «la richiesta deve essere condizionale», non «l'utente deve confermare»                          |
| **502** Bad Gateway           | `E_AI_PROVIDER_ERROR`        | **resta**. Il backend chiama un provider esterno e ne riceve una risposta invalida: è letteralmente la definizione RFC del 502. Normalizzarlo a 500 perderebbe l'unica informazione che serve leggendo i log                                                                                                                  |

> La lezione non è «meno status è meglio». È che **l'uniformità non è un valore
> in sé**: due dei tre sono stati cambiati perché dicevano una cosa falsa, il
> terzo è rimasto perché dice quella vera.

#### ⚠️ Il criterio che distingue un 404 da un 500: chi può rimediare

Prima di scrivere 404 su un «non trovato», chiedersi **chi può fare qualcosa**:

* **l'operatore, cambiando la richiesta** → 404 («quel documento non c'è»);
* **nessuno, finché qualcuno non configura** → **500**. «Non trovato» detto a chi
  non può trovarlo lo manda a cercare una cosa che per lui non esiste.

L'audit del 2026-08-06 sui 404 ha spostato cinque codici per questa ragione:
`E_PIPELINE_NOT_FOUND`, `E_PIPELINE_TASK_HANDLER_NOT_FOUND`,
`E_TASK_IMPLEMENTATION_NOT_FOUND` ed `E_EMITTENTE_DEFAULT_MISSING` → **500**
(pipeline, handler, implementazioni e default mai configurati; uno era già
loggato internamente con `severity="C"` mentre l'HTTP diceva «non trovato»);
`E_LISTINO_VERSIONE_NON_ATTIVA` → **422**, perché non era affatto un
non-trovato — il listino c'è, manca una versione **valida alla data** — e il
fratello `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA` era già 422.

⚠️ **Tre candidati sono stati risparmiati leggendo il codice**, e vale più dei
cinque spostati: `E_PARAMETER_NOT_FOUND` sembrava configurazione mancante, ma è
usato **anche** per l'`override_id` nell'URL di una DELETE, dove il 404 è
corretto (semmai è da spezzare); `E_PREV_STATO_CORRENTE_NON_TROVATO` nasce da
una JOIN che fallisce sia quando il preventivo non esiste (404 giusto) sia
quando il suo stato è rotto; `E_INDIRIZZO_SNAPSHOT_NOT_FOUND` è un
`IF NOT FOUND` su un id referenziato, cioè il 404 «largo» qui sotto.
**Otto candidati dal messaggio, cinque veri dopo la lettura.**

⚠️ **Il nostro 404 è più largo di quello dell'RFC.** Nello standard il 404
riguarda la **risorsa indirizzata dall'URI**; noi lo usiamo anche quando l'URI
esiste ma un'entità **referenziata nel payload** non c'è (`E_FULFILL_NOT_FOUND`,
`E_GESTORE_SOGGETTO_RUOLO_MANCANTE`). È un'estensione diffusa e in questa app è
innocua — nessun interceptor reagisce globalmente al 404 — ma è una scelta, non
la lettura letterale dello standard. L'alternativa RFC-stretta sarebbe 422.

#### Cosa cambia davvero lo status, lato client

> 🔴 **CORREZIONE (2026-08-07): questo paragrafo diceva il contrario, e la cosa
> va letta prima di usarlo per decidere.** Diceva: *«in questa app la maggior
> parte del comportamento la decide `ui_action`, non lo status»*.
>
> **Misurato su tutto il repo: `ui_action` non la legge nessuno.** Né il nome
> (`ui_action`, `uiAction`) né uno solo dei sette valori compare in
> `frontend/src` — o altrove fuori da backend/docs/db. Il frontend legge
> `error.message` (in `useApiHandler.extractErrorMessage`) e lo **status**:
> `>= 500` → toast di sistema, 401 → refresh del token, 401/403 → il polling dei
> contatori si ferma. **Sono tutti e tre gli effetti che esistono.**
>
> 🔴 **AGGIORNAMENTO (2026-08-18): la prima metà di quella misura è scaduta, la
> seconda no — e la differenza è quella che conta.** Rimisurato:
>
> | Cosa | 2026-08-07 | 2026-08-18 |
> | --- | --- | --- |
> | il **nome** in `frontend/src` | zero | **2 occorrenze**, entrambe in `useApiHandler.js`: il commento e `azioneUi.value = err.response?.data?.error?.ui_action ?? null` |
> | i **consumatori** di quel valore | zero | **zero** — `azioneUi` non è letto da nessun componente |
> | i **valori** del vocabolario (`show_error_banner`, `highlight_form_fields`, `show_empty_state`, `redirect_login`, …) | zero | **zero** |
>
> Il campo è arrivato insieme a `fields` (2026-08-08), dallo stesso envelope e
> nella stessa riga: `useApiHandler` **estrae** entrambi, ma solo `campiErrati`
> ha un consumatore. Quindi `ui_action` a quella data era **emessa, trasportata e
> non consumata** — un passo più avanti di «non la legge nessuno», e **zero
> passi** più avanti sul comportamento a video.
>
> ⭐ **AGGIORNAMENTO (2026-09-09): il primo consumatore è arrivato, ed è uno su
> sette.** Rimisurato su `frontend/src`:
>
> | Cosa | 2026-08-18 | 2026-09-09 |
> | --- | --- | --- |
> | i **consumatori** di `azioneUi` | zero | **1** — `useForzaturaConfermata.js`, che ramifica su `CONFERMA_E_RIPETI` |
> | i **valori** del vocabolario nominati nel FE | zero | **1 su 7**: `confirm_and_retry` |
> | gli altri sei (`highlight_form_fields` su 129 codici, `show_error_banner`, `show_toast_error`, `redirect_login`, `show_retry_dialog`, `show_info_banner`) | zero | **zero** |
>
> ⚠️ **Il salto è di categoria, non di quantità**: esiste ora un posto dove un
> componente reagisce a `ui_action`, quindi il campo non è più solo un contratto
> in attesa. ⛔ Ma il punto 3 qui sotto **resta intero**: 129 codici chiedono
> `highlight_form_fields` e a video quella richiesta la serve `campiErrati`, non
> `azioneUi`. Le righe di override (`UI_ACTION_OVERRIDE`, 176 a quella data) vanno riguardate **prima** di accendere il
> secondo consumatore, non dopo.
>
> ✅ E `hint` **non è più lì**: era «emesso, trasportato, zero consumatori» la
> mattina del 2026-09-09 ed è stato reso a video la sera stessa (D4) — vedi
> §Envelope qui sopra. ⭐ Resta il precedente, che è la parte utile: *un campo
> emesso e non consumato non si nota, perché niente fallisce* — e la sola cosa
> che lo ha reso visibile, in entrambi i casi, è stato qualcuno che è andato a
> cercarlo.
>
> ⭐ **DECISIONE (Tid, 2026-09-09): le altre sei `ui_action` sono SERVITE, non
> ignorate — e la voce si chiude dichiarandolo.** Il default del client copre
> l'intero vocabolario tranne `confirm_and_retry`, che è l'unico a chiedere un
> comportamento che il default non sa produrre (una domanda invece di un
> rifiuto):
>
> | valore | chi lo serve oggi |
> | --- | --- |
> | `highlight_form_fields` | **`campiErrati`**, che è l'informazione azionabile: `fields` dice *quale* campo, e senza quello l'`ui_action` non direbbe niente |
> | `redirect_login` | lo **status 401**, in `core/api.js` — il refresh del token, prima ancora che il codice si legga |
> | `show_error_banner` · `show_toast_error` · `show_retry_dialog` · `show_info_banner` | il **toast**, che dal 2026-09-09 porta anche la soluzione e, quando c'è un bersaglio, il gesto |
>
> ⛔ **Non vuol dire che il vocabolario sia inutile**: vuol dire che oggi il
> default è *corretto* per sei valori su sette, quindi ramificarli comprerebbe
> zero. ⚠️ E la condizione per accendere il settimo resta quella già scritta: le
> **righe di override** vanno riguardate **prima**, non dopo — sono state
> decise quando nessuno poteva verificarle a video.
>
> ⚠️ **Le tre conseguenze pratiche qui sotto non cambiano di una virgola**, e
> il punto 3 diventa più concreto: il giorno in cui un componente reagirà a
> `azioneUi` non ci sarà da scrivere l'estrazione — c'è già. Ci sarà solo da
> riguardare le righe di override, **prima** di accenderlo.
>
> ⚠️ **Non vuol dire che `ui_action` sia da togliere**, e nemmeno che le
> decisioni di override siano state inutili: è un contratto **emesso e non
> ancora consumato**, e il costo di tenerlo è zero. Vuol dire tre cose pratiche:
>
> 1. discutere `show_error_banner` contro `highlight_form_fields` oggi **non
>    cambia niente a video** — cambia cosa troverà il frontend il giorno in cui
>    lo implementerà;
> 2. quindi **lo status non è affatto la parte che conta meno**: al momento è
>    l'unica che il client guarda davvero;
> 3. il giorno in cui il frontend leggerà `ui_action`, quelle righe vanno
>    riguardate **prima** di accenderlo, non dopo.
>
> ⚠️ E c'era un difetto conseguente, corretto lo stesso giorno: dei due percorsi
> che costruiscono l'envelope, `exception_to_error_response` spediva `ui_action`
> e `drf_exception_handler` la **calcolava e la buttava via**. Lo stesso codice
> usciva con due forme diverse a seconda di chi lo sollevava. Non se n'era
> accorto nessuno proprio perché a quella data il campo non lo leggeva nessuno —
> ⚠️ e questa è la ragione per cui va corretto **prima** che i consumatori
> crescano: un'asimmetria che oggi nessuno vede, domani è un comportamento che
> cambia a seconda di chi solleva l'errore.

Utile saperlo prima di discutere se un codice è 400 o 409. Gli unici
status con un effetto globale sono:

| Status        | Effetto                                                           | Dove                                      |
| ------------- | ----------------------------------------------------------------- | ----------------------------------------- |
| **401**       | percorso di refresh del token                                     | `src/core/api.js`                         |
| **401 / 403** | il polling dei contatori si ferma                                 | `useQueueCountsPolling`                   |
| **>= 500**    | toast «errore di sistema»: **stesso messaggio**, durata più lunga | `useApiHandler` + `useNotify.systemError` |

Quindi un 500 **non nasconde** il messaggio del database — né lato backend
(`is_technical_code` è una lista chiusa di tre codici, non dipende dallo status)
né lato frontend. Dice «non è colpa tua» a chi legge i log, e lascia il toast più
a lungo a video.

#### Scegliere fra 409 e 400: chi ha scelto il valore in conflitto

È il dubbio più frequente quando due entità «non vanno d'accordo». Il criterio:

* **409 · `show_error_banner`** — l'operatore **non ha un campo da correggere**:
  il conflitto è fra righe che non ha scelto lui (legami creati dal sistema,
  stato del documento cambiato sotto). Il messaggio è «rileggi lo stato»;
* **400 · `highlight_form_fields`** — il valore in conflitto **l'ha scelto lui**
  in un form (un parent, un soggetto, un conto). Il messaggio è «correggi quel
  campo».

Stesso difetto apparente, status diverso: `E_ARTICOLO_MISMATCH` (riga ordine vs
riga DDT, legami di sistema) è 409; `E_ID_FISCALI_DIVERSI` (parent account scelto
a mano) è 400.

#### Il cancello: ogni codice che il DB può nominare deve avere una policy

`apps/core/tests/test_error_codes_db_policy_guardrail.py` — gira in CI a ogni PR
(opt-in `ZEROERP_TEST_DB_E2E=1`, acceso in `ci-validate.yaml`) e confronta
`dbops.vw_codici_errore_da_dichiarare` con il dizionario. Fallisce in tre versi:

1. un codice che il DB può nominare, **senza policy e non nel registro** del
   debito `dbops.codici_errore_senza_policy`;
2. una voce del registro che **ha ottenuto** la sua policy (la riga va tolta dal
   CSV: è debito pagato);
3. una voce del registro che **nessuna funzione viva nomina più**.

⚠️ Dare la classe a catalogo (e rigenerare) a un codice che è nel registro **fa diventare rosso il
cancello** finché il team DB non toglie la riga e riapplica il changeSet
`20260805-37`. Le due metà vanno concordate insieme: è il presidio che fa il suo
mestiere, non un incidente.

⭐ **Dal 2026-08-07 il registro è a zero** (141 → 0 in tre giorni, 150 decisioni).
Due conseguenze pratiche:

* **il verso 1 diventa il presidio vero**: qualunque codice nuovo che il database
  può nominare senza una policy è **rosso il giorno stesso**. Non c'è più un
  arretrato in cui nascondersi;
* **la tabella del registro resta**, vuota. Non si droppa: il cancello la
  interroga a ogni PR, ed è il posto dove atterra un codice nuovo nell'intervallo
  fra il seed DB e la classificazione BE. *Un registro vuoto non è un registro
  inutile: è un registro in pari.*

> Storia completa, criteri e casi: `docs/it/dev/work-done/brief-db-be-terzo-lato-presidio-codici.md`
> e [Presidi e registri del debito §3.4](/guide/presidi-e-registri-del-debito).

#### Come il codice arriva dal DB al backend (dal 2026-08-05)

Gli errori di dominio nascono in PostgreSQL, da `script.fn_log_and_raise_error`.
Il contratto di trasporto è **uno solo**:

> **SQLSTATE `P0001` + campo `CONSTRAINT` valorizzato = errore di dominio**,
> e il contenuto di `CONSTRAINT` è il codice di `config.messaggi_errore`.

Il codice viaggia quindi in un **campo strutturato** dell'eccezione
(`diag.constraint_name` lato psycopg), non nel testo. Gli altri campi restano
dove erano: `DETAIL` = causa, `HINT` = soluzione, e il messaggio è il testo
localizzato per l'operatore. **Il codice non compare nel messaggio, ed è una
scelta**: il messaggio è per l'utente.

⚠️ **La condizione su `P0001` non è prudenza, è necessaria.** Su una violazione
di vincolo vera (classe `23xxx`) `constraint_name` contiene il nome del vincolo
DB (`uq_...`, `fk_...`): leggerlo come codice applicativo scavalcherebbe
`map_integrity_error`, che quei vincoli li traduce già. E se il campo è vuoto va
trattato come assente (`... or None`): quando il codice arriva da un'espressione
che vale NULL, PostgreSQL lo consegna come **stringa vuota**, non NULL.

⚠️ **Il fallback a regex sul testo resta.** Nel DB ci sono 135 `RAISE EXCEPTION`
diretti in 46 funzioni PL/pgSQL che non passano dall'helper: per quelle il campo
esce vuoto. Si potrà togliere il giorno in cui quel numero sarà zero — non prima.

Presidio: `scripts/sql/guardrail_codice_errore_strutturato.sql` (in CI) verifica
che **nessun altro** `RAISE` scriva `CONSTRAINT`. Un secondo mittente su quel
canale non farebbe fallire niente: farebbe rispondere sbagliato.

**Lato backend la lettura è una sola**, in `apps/core/services/db_error_fields.py`
(`structured_db_error_code` → campo, `db_error_code` → campo con ripiego al
testo). Non leggere `diag.constraint_name` a mano: prima del 2026-08-05 la stessa
estrazione era riscritta punto per punto, ognuno col suo modo, ed è così che
si sono sfilati. Oggi i punti di traduzione sono **cinque**, e dal 2026-08-24 leggono
tutti dal BB `diagnostica_db` (sede unica di codice, `hint`, `fields` e bersagli;
il dettaglio è nel docstring di `DiagnosticaDb`). ⚠️ L'elenco va riletto, non dato
per completo: il quinto è stato trovato dopo gli altri quattro.

| Punto                                    | Cosa fa col codice                                                                                                                     |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `ErrorTranslator._from_database_error`   | lo usa come `ApiError.code` (→ policy → status)                                                                                        |
| `payload_helpers.translate_db_errors`    | lo usa al posto del `fallback_code` di dominio                                                                                         |
| `ErrorManager.raise_from_database_error` | lo usa **sempre**, con la **frase del DB** (`message_primary`); i `known_markers` e il `message` del chiamante restano il ripiego dei soli `RAISE` diretti senza campo. ⚠️ Fino al 2026-09-23 lo accettava solo se dichiarato, col `message` del chiamante: un guard comune (le date di validità, 25 tabelle) usciva come codice generico o come «Violazione vincolo contrattuale.» — brief-db-guard-date-validita §13 |
| `pipeline_step_executor._run_per_fattura_task` | la strada del pilota: codice, `hint`, `fields` e bersagli da `diagnostica_db` |
| `pratiche_service._raise_known_db_error` | lo accetta se dichiarato dal dominio, con la frase del DB; un codice non dichiarato è **rilanciato nudo** e il middleware (riga 1) lo traduce allo stesso modo |

Test: `apps/core/tests/services/test_db_error_fields.py` — 8 unitari sulla
precedenza campo/testo e 3 end-to-end su DB reale (saltati se il DB non
risponde), fra cui il caso in cui la regex **non** trova nulla e il campo sì.

#### ⚠️ 57 codici ereditati fuori convenzione

`ErrorPolicyRegistry.resolve` ha una scorciatoia — codice non registrato ma che
comincia per `E_` → 400 «errore di validazione» — e **tutto il resto cade su
`E_GENERICO`, cioè 500**. Al 2026-08-05 nel DB c'erano 57 codici che il prefisso non ce
l'hanno (`PRATICHE_TRANSIZIONE_NON_AMMESSA`, `PREV_*`, `FLUSSI_*`,
`ERRORE_PARAMETRI`, `CF_NON_VALIDO`…), usati da 77 call site.

Quattro di quei 57 sono usciti dal seed perché nessuno li sollevava più
(`20260805-11`): **restano 53**. Di questi, **23 sono già registrati** col nome
storto — per i loro 29 call site il campo strutturato è un guadagno secco: oggi
sono mascherati da `E_DATABASE`, domani arrivano alla loro policy. **I 30 senza
policy** (48 call site in 26 funzioni) sono quelli che passerebbero da 400 a 500,
e vanno registrati **prima o insieme** all'adozione del campo.
Al 2026-10-25 nel dizionario generato ne restano 49, **tutti ritirati**
(`CODICI_RITIRATI`): risolvono ancora per il diario, nessuna funzione viva li nomina.

⚠️ Fino al 2026-08-07, col dizionario scritto a mano, registrare un codice già
presente lo sovrascriveva in silenzio (in un dict literal l'ultima chiave vince).
Oggi la mappa codice → classe è **generata** dal catalogo e non si tocca; il rischio
resta solo su `error_ui_overrides.py`, l'unico dict scritto a mano.

Decisione del 2026-08-05: **si registrano così come sono** (oggi hanno la loro
classe in `error_policies_generated.py` come tutti gli altri) — rinominarli
costerebbe seed + call site + pgTAP senza comprare nulla —
**e il rubinetto si chiude**: il controllo (B) del guardrail rifiuta ogni codice
*nuovo* fuori convenzione. I 57 ereditati vivono in
`dbops.messaggi_errore_codici_legacy`, che è un **registro del debito e deve
calare**.

⭐ **Dal 2026-08-07 è a zero righe** (l'ultima è uscita col rename
`MESSAGGIO_NON_DEFINITO` → `E_MESSAGGIO_NON_DEFINITO`).

⛔ **La tabella NON si droppa** — decisione di Tid, 2026-08-08. Questa riga
diceva il contrario, ed è stata corretta: a zero righe droppare sarebbe
*neutro* nel comportamento (il `NOT EXISTS` del controllo (B) non toglie nulla,
il (C) è vero a vuoto), ma comprerebbe «meno codice» al prezzo di **mettere mano
al controllo (B)**, cioè all'unica cosa che tiene la convenzione.

La seconda ragione è che il meccanismo **serve alla prossima eredità**: il
progetto ne ha già assorbita una (57 codici) e ne assorbirà altre. Ricostruire
tabella, CHECK e due controlli sotto la pressione di un'importazione è il momento
in cui li si costruisce male.

⛔ **Non è però una «valvola per le eccezioni», e la distinzione è operativa.**
L'unica eccezione vera mai arrivata — la famiglia `W_` dei warning — **non è
finita nel registro: è stata allargata la convenzione** (`20260805-28`), ed era
la scelta giusta. Le tre strade sono diverse:

| Cosa arriva                                         | Dove va                         | Perché                                                |
| --------------------------------------------------- | ------------------------------- | ----------------------------------------------------- |
| una **famiglia** nuova con una semantica sua (`W_`) | si **allarga la regola**        | una famiglia dentro un registro di eccezioni si perde |
| un codice **ereditato** da fuori, già storto        | **il registro**                 | è debito: ha una data e deve calare                   |
| un codice **nuovo** nato storto                     | si **corregge prima del merge** | non è debito, è un difetto                            |

Per questo la tabella **non ha una colonna `motivo`** e non deve averla:
risponderebbe a «perché questa eccezione è legittima», che è la domanda della
prima riga — quella che non passa di qui. Per il debito l'orologio c'è già ed è
`data_registrazione`.

⚠️ **Nota sul perché la convenzione conta, corretta il 2026-08-08.** Fino al B-5
la ragione era «un codice fuori convenzione non trova policy e cade su
`E_GENERICO`, cioè 500». **Non è più così**: `error_policies_generated.py` è
generato dal catalogo e li contiene tutti, e `resolve()` cerca prima il nome
esatto. La regola resta per due ragioni più strette — la **finestra** fra il
migrate che crea il codice e il commit che rigenera il dizionario (lì a decidere
400 invece di 500 resta il prefisso), e la **separazione `E_`/`W_`**. Il
messaggio del controllo (B) è stato riscritto di conseguenza: una regola che si
spiega con un fatto scaduto insegna una cosa falsa a chi si fida.

⚠️ Da non confondere con `dbops.codici_errore_senza_policy` (il registro del
*terzo lato*, 141 → 0): è un'altra tabella, un altro mestiere, e anche quella
resta.

**Eccezione — codici middleware-level.** Alcune risposte sono costruite
direttamente da `JwtAuditMiddleware` (helper `_json_error`, stesso envelope)
e **non** passano dall'exception handler / `error_policies.py`. (Fino al
2026-09-28 c'era anche `E_USER_DISABILITATO`, dal rifiuto in `process_view`:
ritirato perché per i client Bearer non scattava mai. Dal 2026-10-02 non
c'e' piu' nemmeno un `DISABILITATO` da rifiutare: una veste spenta e'
`attivo = false` col suo tipo, R-DB-1.)

| Codice                | HTTP | Quando                                                                                                                                                                                                           |
| --------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_GUC_RESET_FAILED`  | 500  | il reset GUC d'inizio richiesta è fallito (fail-closed, vedi §GUC)                                                                                                                                               |
| `E_DB_ROLE_UNSAFE`    | 500  | la connessione del percorso richiesta è su un ruolo `BYPASSRLS` (guard fail-open RLS: `DB_USER` misconfigurato sul ruolo batch, o canale di sistema usato per errore nel web → richiesta rifiutata, fail-closed) |

Non passare dal traduttore non li esenta dal catalogo: sono a catalogo come
`TECNICO` (dal 2026-10-07), con frase di ripiego, e lo status scritto a mano dal
middleware coincide con quello della classe.

#### Codici auth multi-veste (§8.3 PR-B1)

| Codice                  | HTTP | UI action         | Quando                                                                          |
| ----------------------- | ---- | ----------------- | ------------------------------------------------------------------------------- |
| `E_VESTE_NON_ATTIVA`    | 403  | show_error_banner | Login o refresh su un namespace senza identita con la veste richiesta           |
| `E_JWT_SENZA_IDENTITA`  | 401  | redirect_login    | JWT senza claim `identita_id` (token pre-refactor multi-face)                   |
| `E_IDENTITA_NON_ATTIVA` | 401  | redirect_login    | Claim `identita_id` non corrisponde a identita attiva (revocata dopo emissione) |

Vedi [api_multi_veste_token.md](../backend/core/manual/api_multi_veste_token.md)
per il contratto completo.

#### Codici invito/attivazione portale + shop (§8.4 PR-B2 + §13.7 B1)

| Codice                     | HTTP | UI action         | Quando                                                                                                                           |
| -------------------------- | ---- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `E_INVITO_PORTALE`         | 400  | show_error_banner | Errore admin durante invio/reinvio invito portale o shop (validazione, identita gia' attiva, veste non supportata)               |
| `E_ATTIVAZIONE_PORTALE`    | 400  | show_error_banner | Errore consume token attivazione portale (token assente/scaduto, password mismatch, identita rimossa)                            |
| `E_ATTIVAZIONE_SHOP`       | 400  | show_error_banner | Errore consume token attivazione shop (simmetrico portale, B1 §13.7)                                                             |
| `E_ATTIVAZIONE_SHOP_CROSS` | 400  | show_error_banner | Errore attivazione cross-veste shop dal profilo portale (veste non CLIENTE_PORTALE, identita gia' su altro auth_user, GUC vuota) |

Vedi [api_invito_portale_shop.md](../backend/core/manual/api_invito_portale_shop.md)
per il contratto completo dei flussi invito + attivazione portale e shop.

### Test

Test progressivi insieme allo sviluppo, **tre livelli** — erano due fino al
2026-09-09, quando ci si è accorti che il terzo esisteva già da mesi e nessun
documento lo nominava:

| Livello                       | Dove                                          | Cosa                                                                                                                                                       | DB reale | In CI                          |
| ----------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------ |
| Unit test service / API       | `apps/*/tests/services/`, `apps/*/tests/api/` | Validazione, dedup, not found, orchestrazione, envelope (repository mockati)                                                                               | No       | ✅ sempre                       |
| **Guardrail su DB provvisto** | `apps/*/tests/db/` + i guardrail di `core`    | La **giuntura**: che `diag.constraint_name` sopravviva a libpq, che ogni codice del DB abbia una policy, che i tipi di handler della coda esistano davvero | Sì       | ✅ via `ZEROERP_TEST_DB_E2E=1`  |
| Smoke end-to-end              | `backend/scripts/tests/smoke-*` (`.py`, `.sh`) | Percorsi reali: i `.py` in `transaction.atomic()` + `set_rollback(True)`, i bash via HTTP                                                                                      | Sì       | ⛔ no — ogni notte su sviluppo |

Quando si crea o tocca un service, si scrivono/aggiornano i test corrispondenti.

⚠️ **Un test mockato non vede la giuntura, e il type checker sì.** Un `MagicMock` accetta
qualunque attributo: un test che dichiara `repo.metodo.return_value = …` resta verde anche il
giorno in cui `metodo` non esiste più. È successo (riallinea e sblocca prezzo di commessa, sei
mesi di 500 con il test verde). Dal 2026-10-08 lo vede **mypy** in CI, a cricchetto
([sicurezza-e-qualita-statica.md](sicurezza-e-qualita-statica.md) §mypy); la chiamata vera la
prova solo il secondo livello qui sotto.

⭐ **Il secondo livello si accende con `richiedi_db_provvisto`**
(`apps/core/tests/db_e2e.py`); il numero dei file che lo usano lo stampa
`scripts/indicatori-qualita-be-fe.sh` ([indicatori](qualita-be-fe-indicatori.md)). È
l'unico che vede il pezzo in mezzo: i pgTAP coprono il lato DB, i test unitari col
`diag` finto coprono il lato Python, e **nessuno dei due vede la giuntura**.

⚠️ **Il terzo livello non è un cancello**: la CI non lo lancia. Dal 2026-10-13 lo
lancia però il **giro notturno** sul DB di sviluppo (§«Gli smoke» qui sotto):
una regressione arriva nel digest delle 7, non blocca un merge.

#### Convenzioni dei file di test

* Struttura per app: `apps/<schema>/tests/` con almeno `api/` e `services/`.
* In testa a ogni file, un breve indice dei test (nome test/caso); negli smoke
  bash (`backend/scripts/tests/smoke-test-*.sh`) un blocco `# Indice test (0..N):`
  dopo l'header.
* ⛔ Uno smoke bash nuovo, subito dopo `BASE_URL=`, include
  `source "$(dirname "${BASH_SOURCE[0]}")/_smoke_https.sh"`: parla con Gunicorn
  diretto in HTTP, e fuori da `DEBUG` Django redirige in HTTPS (301). Il file si
  dichiara HTTPS come Nginx, e come Nginx dichiara la **provenienza**
  (`X-Forwarded-For: 127.0.0.1`): senza, il login risponde
  `E_AUTH_CHIAMATA_NON_VALIDA` (freno sulla credenziale, fail-closed). Presidio:
  `apps/core/tests/api/test_https_header.py`.
  I test Django non ne hanno bisogno: il redirect lo spegne il runner.
* ⛔ Uno smoke bash che fa il **login** include, subito dopo `BASE_URL=`, solo
  `source "$(dirname "${BASH_SOURCE[0]}")/_smoke_auth.sh" "$@"` (porta con sé
  `_smoke_https.sh`, `_smoke_secondo_fattore.sh` e `_smoke_refresh.sh`) e chiama
  **`smoke_login`** (opzioni `-D`, `--login-vero`, `--senza-prompt`, `--uscita N`).
  Se l'utente degli smoke ha il secondo fattore attivo, il secondo passo lo fa il
  BB col codice calcolato da **`SMOKE_TOTP_SECRET`**; il DB accetta un codice per
  intervallo di 30 secondi, e fra due login il BB **aspetta** il codice nuovo. Un
  login che il BB non copre resta `curl_login` con `# login esplicito: <perché>`.
  Utente da `SMOKE_USER`, mai scritto a mano. Login unico per un giro di smoke:
  `eval "$(scripts/tests/smoke-login.sh)"` (run-book §11). Il refresh non è più
  nel corpo del login ma nel cookie `zeroerp_refresh`: lo si legge dal
  `Set-Cookie` (`smoke_login -D`) e ripresenta con `curl_refresh`. Presidio:
  `test_https_header` 13, 15–18.
* ⛔ **Ogni patch di un repository ha `autospec=True`**: la classe
  (`patch("…XRepository", autospec=True)`, `patch.object(modulo, "XRepository",
  autospec=True)`) e il metodo (`patch.object(XRepository, "metodo", autospec=True)`,
  `patch("…XRepository.metodo", autospec=True)`).
  Un mock libero accetta metodi e parametri che il repository non ha: il test resta
  verde dopo una rinomina, e `assert_not_called()` su un nome sparito passa a vuoto.
  Col mock `autospec` il nome sbagliato è `AttributeError`, il parametro sbagliato
  `TypeError`. Due conseguenze: il mock di un **metodo** registra anche `self`, quindi
  negli `assert_called_*` il primo argomento è `mock.ANY`; un repository finto passato
  come `return_value=` nasce da `create_autospec(XRepository, instance=True)`, non da
  `MagicMock()`. Un metodo che una classe base di test patcha già (per esempio
  `AuthRepository.get_fatti_obblighi` in `JwtMockedApiTest`) si **configura** dal mock
  che la base espone, non si ripatcha: una seconda patch `autospec` è `InvalidSpecError`.
  Esenti le patch che passano già l'oggetto sostitutivo (`new`). Presidio, con la
  storia del giro che l'ha introdotta: `apps/core/tests/test_presidio_autospec_repository.py`.
* Esecuzione: `./manage-test.sh apps.core.tests.api -v 2`. Smoke di docs/schema:
  `apps/core/tests/api/test_diagnostics_api.py`.

#### Test Django in CI: senza dipendere da un DB reale

* ⛔ **`unittest.TestCase` e `SimpleTestCase` non sono equivalenti**: solo
  `SimpleTestCase` **impedisce** al codice sotto test di parlare col database
  (`DatabaseOperationForbidden`). `unittest.TestCase` glielo *permette*
  soltanto — quindi un mock dimenticato lì non fallisce: parla col DB di
  sviluppo, e il test resta verde raccontando una cosa che in CI non succede.
  Per i test unitari con mock si usa `SimpleTestCase`; `unittest.TestCase`
  resta legittimo solo dove il test non tocca Django affatto (una funzione
  pura). Il pregresso che usa l'altra forma è un debito, non un modello.
* ⚠️ **Nessun test dichiara un database** (`django.test.TestCase`,
  `TransactionTestCase`, `databases = [...]`), quindi il runner stampa
  «Skipping setup of unused database(s)» e la connessione resta quella
  **configurata**, un DB con lo schema Liquibase completo. Ci si appoggiano i
  test del secondo livello (`test_db_error_fields.py`, il guardrail dei codici).
  **Il primo test che dichiarerà un database farà creare al runner un DB vuoto
  per TUTTA la suite**, e quei test falliranno in una PR che non c'entra: non è
  un divieto, ma vanno adeguati nello stesso commit.
* **Ogni accesso al DB si mocka** (cursor, advisory lock, query dirette):

  ```python
  def setUp(self):
      patcher = patch.object(MyClass, "_metodo_che_usa_db", return_value=valore)
      self._mock = patcher.start()
      self.addCleanup(patcher.stop)
  ```

* Ogni `APIView` su `/api/v1/` ha `@extend_schema` su ogni metodo HTTP pubblico,
  con `request` (se il metodo ha un corpo) **e** `responses`: senza uno dei due
  drf-spectacular non trova il serializer (`W002`) e l'endpoint esce vuoto
  dallo schema. Lista e dettaglio (`/x/`, `/x/{id}/`) avrebbero lo stesso
  `operationId` (`W001`): li separa l'hook `nomi_lista_dettaglio`
  (`apps/core/api/openapi_extensions.py`) in `x_list` / `x_retrieve`, senza
  toccare le view; le altre collisioni vogliono `operation_id=` esplicito.
  Presidio dal 2026-09-26:
  `apps/core/tests/test_schema_openapi_registro.py`, registro a cricchetto
  `openapi_schema.baseline.json` — rosso su una view o un `operationId` nuovi,
  rosso anche su una voce sanata e non tolta. ⚠️ Il `W002` è **per view**: una
  view ancora nel registro non è protetta sugli altri metodi.
* **Prova locale come la CI**:

  ```bash
  DB_HOST=localhost DB_PORT=5432 DB_NAME=zeroerp DB_USER=zeroerp_app DB_PASSWORD=secret-app \
  DJANGO_SECRET_KEY=ci-placeholder DJANGO_FIELD_ENCRYPTION_KEYS="$(printf ci-placeholder-fernet-key-32byte | base64)" DJANGO_SECURE_HSTS_SECONDS=0 \
  DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1" DJANGO_DEBUG=0 DJANGO_TRUSTED_PROXY_COUNT=0 FRONTEND_URL=https://localhost \
  ZEROERP_TEST_DB_E2E=1 DJANGO_API_SEARCH_THROTTLE_RATE=100000/min DJANGO_REQUEST_LOG_ENABLED=0 CACHE_BACKEND=locmem \
  .venv/bin/python manage.py test -v 2
  ```

  ⚠️ Senza `ZEROERP_TEST_DB_E2E=1` il secondo livello (i guardrail sul DB) si salta
  in silenzio. La fonte delle variabili è `.github/workflows/ci-validate.yaml`.

  ⚠️ `DB_USER=zeroerp_app`, non `zeroerp`: l'owner salta la RLS, e un test
  no-leak sul DB vero con lui va rosso. Presidio: `richiedi_ruolo_soggetto_a_rls`
  in `apps/core/tests/db_e2e.py`.

#### Gli smoke

Due famiglie in `backend/scripts/tests/`, un runner solo:

| | `smoke-*.py` | `smoke-test-*.sh` |
| --- | --- | --- |
| Come parlano | in-process (`./manage-env.sh shell <`), col database di sviluppo | via **HTTP** col backend in esecuzione (`BASE_URL`), utente degli smoke di `backend/env.sh` (`dev.smoke`, dal provisioning di sviluppo: run-book §11) |
| Cosa lasciano | niente: `transaction.atomic()` + `set_rollback(True)` | ⚠️ **scrivono** sul database di sviluppo (documenti di prova sull'emittente attivo dell'utente degli smoke) |

⛔ Non li raccoglie il runner Django e non li esegue la CI. Li lancia
`scripts/smoke-baseline.sh`, a mano o **ogni notte**: dal 2026-10-13 il management
command `smoke_notturno` (timer `zeroerp-smoke-notturno`, 02:30) gira il runner sul DB
di sviluppo, e con una regressione la corsa chiude `ok=false` e finisce nel digest
delle 7. ⛔ **Solo sviluppo**: la sveglia è spenta di default e il processo non
si accende in PRODUZIONE (catalogo `dbops.processi`, colonna `accendibile_in_produzione`,
nessun «Esegui ora»), perché i bash scrivono. Fino al 2026-10-18 lo chiedeva anche
`SMOKE_NOTTURNO_CONSENTITO=1` nell'ambiente: ritirato quando il divieto è entrato nel modello. Fino al 2026-10-12 il runner prendeva i soli `.py`: i bash non li
lanciava nessuno, e al primo giro completo erano rossi piu' della meta'.

```bash
scripts/smoke-baseline.sh                   # tutti (Python ~4 min, piu' i bash)
scripts/smoke-baseline.sh fattura-scadenze  # solo quelli col nome dato
scripts/smoke-baseline.sh --update          # rigenera il registro dei noti
```

Stessa forma di `pgtap-baseline.sh`: non-verde **noto** → silenzio, **nuovo** →
`exit 1`, noto rientrato → segnalato. Registro:
`backend/scripts/tests/baseline-smoke.tsv`, un debito che deve calare.

* ⛔ **Il codice di uscita di uno smoke non dice la verità**: uno stampa «ESITO:
  FALLITO» ed esce 0. Lo script classifica dall'**output**.
* ⚠️ **Gli esiti sono tre**: oltre a verde e rosso c'è `SENZA_MATERIA` (una
  precondizione assente, dichiarata con `raise SystemExit`). La copertura di quel
  giro vale zero, non «parziale».
* **I bash** fanno un login solo per il giro (`smoke-login.sh`), rinnovato quando
  il token sta per scadere; su un `429` (freno dei login, o delle ricerche: 30 al
  minuto per IP) aspettano e riprovano una volta (`LIMITE_RICHIESTE` se non
  basta). Chi non si puo' lanciare
  nell'ambiente (es. `smoke-test-ai-assistant.sh` senza `AI_PROVIDER=mock`) e'
  **stampato** fra gli esclusi, mai saltato in silenzio. ⛔ Escluso anche
  `smoke-c9-fatturazione-parte-alta.py`, salvo chiamarlo per nome
  (`scripts/smoke-baseline.sh c9`): è l'unico che **non fa rollback** — approva,
  emette fatture e consuma la numerazione fiscale — quindi non può stare nel giro
  di ogni notte. Uno smoke che chiude con
  dei `SKIP` nel riepilogo e' `PARZIALE`, non verde: i passi saltati valgono zero.
* ⏱ A fine giro lo script stampa i **tempi**: durata del giro, quanto ha atteso
  sul freno e gli smoke piu' lenti. Un giro che nessuno ha tempo di lanciare non
  protegge niente: i rimedi alla lentezza si scelgono su questi numeri.

---

## Checklist nuovo endpoint

1. Creare la view ereditando dalla porta giusta: `DomainAPIView` (o `AdminAPIView`
   per amm-software, `PortaleAPIView`, `ShopAPIView`)
2. Definire `area_funzionale` sulla classe
3. List + Create sulla stessa URL: `def get` + `def post`
4. Detail + Update sulla stessa URL: `def get` + `def patch`
5. POST: `handle_post_json` con handler che chiama il **service**; PATCH/PUT:
   `corpo_oggetto(request)`, mai `request.data` grezzo (§Endpoint PATCH)
6. Una POST che scrive porta l'`Idempotency-Key` (senza: 400
   `E_IDEMPOTENCY_KEY_REQUIRED`, da `_ApiViewBase.initial()`); una POST che **legge**
   dichiara `post_accesso = "view"`. In modalità forte, un'operazione a passi dichiara
   `unita_di_lavoro=UnitaDiLavoro.A_PASSI` e si registra in `test_unita_di_lavoro.py`
   (§Idempotency-Key)
7. Per GET: usare `success_response()`; per le liste la finestra si legge con
   `pagina_da_query` (o `parse_list_params`) e l'envelope si costruisce con
   `envelope_da_offset` (o direttamente dal BB `fetch_paged_with_total`), §Paginazione
8. Aggiungere `@extend_schema` con `request` e `responses`. Lo schema del **corpo** di una
   scrittura si legge dal contratto del service con `schema_da_contratto` (chiavi ammesse +
   dizionario dei tipi del dominio): una chiave senza tipo è un errore all'import.
   `inline_serializer` resta per le risposte e per i corpi che non hanno un contratto
9. Registrare la route nell'urlconf dell'app (`urls_v1.py` o `urls.py`, §Struttura tipo per app)
   con name `<dominio>-<risorsa>-list` / `<dominio>-<risorsa>-detail`
10. Scrivere test service in `tests/services/` (validazione, dedup, not found), test API
    con `JwtMockedApiTest` (il suo `ClientApi` mette già la key; chi prova l'assenza usa
    `Client`) e, se l'endpoint chiama una funzione del DB, un test sul DB vero
    (`richiedi_db_provvisto`)
11. Documentare la rotta in `docs/it/backend/<dominio>/manual/`: la copertura la
    controlla `core/tests/test_copertura_doc_api.py`
12. Se endpoint di ricerca: `is_search_endpoint = True`
13. Registrare i codici errore prima dell'uso: il codice nasce **a catalogo**
    (`config.codici_errore`, con la sua classe — richiesta al team DB), poi
    `./manage-env.sh genera_error_policies` lo porta nel backend. Status e
    `ui_action` si derivano dalla classe; il modulo generato non si tocca a mano

---

## Disattivazione record — ordine UPDATE e trigger

Il database usa trigger `dbops.trgfn_prevent_deactivate_if_children` sulle tabelle con
campo `attivo`, generati dall'automazione ATTIVO a partire dalle FK. Il trigger
**impedisce di disattivare un padre se ha figli attivi**.

Questo vale per tutte le relazioni padre-figlio dove entrambi hanno `attivo` e c'è
una FK. Dove la FK manca il guard è scritto a mano, con la stessa regola: per
esempio `risorse_umane` → l'identita' OPERATORE della stessa persona in
`anagrafiche.identita_digitali` (`anagrafiche.trgfn_risorse_umane_guard_identita_attiva`,
codice `E_RISORSA_UMANA_IDENTITA_ATTIVA`, dal 2026-09-12).

⚠️ Fino al 2026-09-12 l'esempio qui sotto scriveva su
`risorse_umane_auth_user`: era il **nome vecchio** del ponte. La vista è stata
ritirata lo stesso giorno (`90_end/20260912-26`), e il guard che la leggeva è stato
sostituito da quello scritto a mano (`20260912-18`/`-19`): chi scrive passa da
`identita_digitali`.

### Regola: disattivare dal basso verso l'alto, riattivare dall'alto verso il basso

**Disattivazione** — prima i figli, poi il padre:

```python
# 1. Disattiva figlio
UPDATE anagrafiche.identita_digitali SET attivo = false WHERE ...
# 2. Disattiva padre (trigger OK: figlio gia' inattivo)
UPDATE anagrafiche.risorse_umane SET attivo = false WHERE ...
```

**Riattivazione** — prima il padre, poi i figli:

```python
# 1. Riattiva padre
UPDATE anagrafiche.risorse_umane SET attivo = true WHERE ...
# 2. Riattiva figlio (padre gia' attivo)
UPDATE anagrafiche.identita_digitali SET attivo = true WHERE ...
```

### Perche'

Il trigger e' una guardia di integrita': un figlio attivo senza padre attivo
non ha senso nel dominio. Se il codice Python non rispetta l'ordine, il trigger
blocca l'operazione con `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` (figlia con `attivo`: il
rimedio è disattivarla) o `E_ATTIVO_BLOCK_CHILDREN_EXIST` (figlia senza `attivo`:
blocca su qualunque riga collegata, il rimedio è toglierla), oppure col codice del
guard dedicato.

Questa regola si applica a **qualsiasi** operazione di disattivazione/riattivazione
nel sistema, non solo agli operatori. Quando si implementa un nuovo endpoint
`disabilita`/`riattiva`, verificare le relazioni padre-figlio e rispettare l'ordine.
