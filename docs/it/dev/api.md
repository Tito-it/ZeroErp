# Linee guida API

> Destinatari: sviluppatori backend di Zero ERP
> Aggiornato: 15 marzo 2026
>
> Vedi anche:
>
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

| | Esempio | Perche' |
| --- | --- | --- |
| OK | `POST /toponomastica/` | Il metodo POST dice "crea" |
| NO | `POST /toponomastica/crea/` | Il verbo e' nel metodo HTTP, non nel path |
| NO | `PATCH /toponomastica/5/aggiorna/` | Idem |

### Azioni di dominio — verbo ammesso come ultimo segmento

Operazioni non-CRUD (cambio stato, sospensione, esecuzione pipeline) usano un verbo
breve come ultimo segmento. Il verbo nomina **cosa** e', non descrive *come* si fa.

| | Esempio | Perche' |
| --- | --- | --- |
| OK | `POST /pratiche/3/stato/` | `stato` e' la sotto-risorsa che cambia |
| OK | `POST /pratiche/3/sospendi/` | Azione atomica, nome diretto |
| NO | `POST /pratiche/3/aggiorna-stato/` | Descrizione dell'azione, non nome della risorsa |
| NO | `POST /pratiche/3/esegui-sospensione/` | Descrive l'azione invece di nominarla |

### Lookup — due pattern, una regola

Per i dropdown/select nel frontend esistono due pattern complementari:

**1. Lookup generico** — per tabelle config con struttura `id, codice, descrizione`:

```text
GET /api/v1/core/lookup/codici/?rel=config.qualifiche
GET /api/v1/core/lookup/codici/?rel=config.stati_pratiche&search=ape
```

Un'unica API, parametro `rel` con whitelist (~45 tabelle config).
Restituisce sempre `id, codice, descrizione` con paginazione e search.

**2. Lookup dedicato** — quando servono JOIN o campi extra non riducibili a `id, codice, descrizione`:

```text
GET /api/v1/anagrafiche/province/lookup/     → sigla + regione_descrizione
GET /api/v1/anagrafiche/regioni/lookup/      → stato_descrizione
GET /api/v1/anagrafiche/stati/lookup/        → codice_iso2
```

Suffisso `/lookup/` sulla risorsa, senza paginazione.

**Regola:** usare il lookup generico quando la tabella ha la struttura standard
(`id, codice/codice_interno, descrizione`). Creare un lookup dedicato solo se
servono colonne aggiuntive da JOIN o campi non standard.

| Criterio | Lookup generico | Lookup dedicato |
| --- | --- | --- |
| Struttura | `id, codice, descrizione` | Campi custom, JOIN |
| Endpoint | `GET /core/lookup/codici/?rel=...` | `GET /{risorsa}/lookup/` |
| Paginazione | Si' | No (lista completa) |
| Quando usare | Tabelle config standard | Province, regioni, stati, UO con gerarchia |

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
    views.py          # APIView per ogni endpoint
    urls.py           # Route unversioned (diagnostics/test)
    urls_v1.py        # Route canoniche /api/v1/<dominio>/
  services/           # Orchestrazione e logica Python
  db/                 # Repository con raw SQL (cursor)
  types.py            # TypedDict per tipizzare le righe DB
  tests/
    api/              # Test endpoint HTTP
    services/         # Test logica service
```

---

## Base classes per view

Due base class in `apps/core/api/base_views.py` eliminano il boilerplate auth/permission:

```python
from apps.core.api.base_views import DomainAPIView, AdminAPIView

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
```

| Base class | Auth | Permessi | Uso |
| --- | --- | --- | --- |
| `DomainAPIView` | JWT | `ZeroERPPermission` + `area_funzionale` | Endpoint di dominio |
| `AdminAPIView` | JWT | `IsAdminZeroERP` (check diretto ruolo_sistema) | Amm. Software |

### Attributi di classe

| Attributo | Scopo | Obbligatorio |
| --- | --- | --- |
| `area_funzionale` | Schema DB dell'area (es. `"vendite"`, `"anagrafiche"`) | Si' su DomainAPIView |
| `is_search_endpoint` | Abilita `SearchBurstRateThrottle` | No |
| `post_permission` | Codename azione di processo (per comandi specifici) | No |
| `skip_area_check` | Salta il check area — ammesso solo per endpoint cross-dominio (profilo, sessioni, lookup) | No |

### Pattern Dual-Class (ELIMINATO)

Il pattern Base + V1 e' stato eliminato il 15 marzo 2026.
Tutti i moduli usano ora `DomainAPIView` o `AdminAPIView` direttamente:

```python
class ApiRunLottoPipeline(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "genera_fatture_lotti"

    def post(self, request): ...
```

Non creare classi V1 per nuovi endpoint.

La risoluzione permessi segue la catena: superuser bypass → ruolo_sistema → azione processo → livello area/oggetto CRUD. Vedi `apps/core/api/permissions.py`.

---

## Endpoint POST (Command API)

### `handle_post_json` — helper obbligatorio

Tutti gli endpoint POST usano `handle_post_json` da `apps.core.api.endpoint_helpers`.
Il helper gestisce in modo centralizzato:

1. Parsing JSON del body (`parse_json_body`)
2. Validazione `Idempotency-Key` (se `require_idempotency_key=True`)
3. Idempotency strong mode (claim/replay/in_progress su `dbops.idempotency_keys`)
4. Esecuzione handler e wrap in `success_response`
5. Gestione errori con `exception_to_error_response`

```python
from apps.core.api.endpoint_helpers import handle_post_json

class ApiPraticaStato(APIView):
    # Scopo: Gestisce la richiesta HTTP POST per cambiare stato pratica.
    def post(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            pratiche_service.cambia_stato_pratica(pratica_id, str(payload["nuovo_stato"]))
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)
```

### Validazione parametri

I parametri del payload si estraggono con i validator di `apps.core.api.payload_validators`:

| Funzione                                       | Scopo                                         |
| ---------------------------------------------- | --------------------------------------------- |
| `optional_int(payload, "key")`                 | Estrae int o None, errore se non convertibile |
| `optional_bool(payload, "key", default=False)` | Estrae bool con default                       |
| `optional_iso_date(payload, "key")`            | Estrae `date` da stringa ISO                  |
| `optional_uuid(payload, "key")`                | Estrae UUID                                   |

### Idempotency-Key

| Regola          | Dettaglio                                                                               |
| --------------- | --------------------------------------------------------------------------------------- |
| Header          | `Idempotency-Key` (stringa libera, tipicamente UUID)                                    |
| Obbligatorieta` | `require_idempotency_key=True` su tutti gli endpoint che modificano stato               |
| Strong mode     | Attivabile con `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1`                                |
| Store           | Tabella `dbops.idempotency_keys`                                                        |
| Replay          | Key gia` completata: restituisce risposta cached con header `X-Idempotency-Replayed: 1` |
| In-progress     | Key gia` in elaborazione: `409` con codice `E_IDEMPOTENCY_IN_PROGRESS`                  |

---

## Endpoint GET (Read API)

Gli endpoint di lettura restituiscono dati senza modificare lo stato.

```python
class ApiLottiList(APIView):
    is_search_endpoint = True                           # abilita throttling

    # Scopo: Restituisce via GET l'elenco paginato dei lotti fatturazione.
    def get(self, request: Request) -> JsonResponse:
        competenza_mese = optional_iso_date(
            {"competenza_mese": request.query_params.get("competenza_mese")},
            "competenza_mese",
        )
        page = optional_int({"page": request.query_params.get("page", "1")}, "page")
        page_size = optional_int(
            {"page_size": request.query_params.get("page_size", "50")}, "page_size"
        )
        auth_user_id = get_scope_user_id(request)       # None per superuser

        data = fn_list_lotti(
            competenza_mese=competenza_mese,
            auth_user_id=auth_user_id,
            page=page,
            page_size=page_size,
        )
        return success_response(data)
```

### Paginazione

| Parametro   | Default | Max |
| ----------- | ------- | --- |
| `page`      | 1       | —   |
| `page_size` | 50      | 200 |

Risposta paginata:

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

Pattern alternativo (per endpoint che usano `limit`/`offset`):

```json
{
  "data": {
    "count": 142,
    "results": [...]
  }
}
```

### Ricerca e throttling

* `is_search_endpoint = True` sulla view abilita `SearchBurstRateThrottle`
* Ricerca testuale: parametro `search`, minimo 3 caratteri, operatore ILIKE
* Vedi: `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md`

---

## Endpoint PATCH (aggiornamento parziale)

Usato quando un'entita` ammette modifica di campi specifici senza che questo costituisca un'azione di dominio distinta (es. aggiornare descrizione o scadenza di una pratica).

```python
class ApiPraticaDetail(APIView):
    # Scopo: Gestisce la richiesta HTTP PATCH per aggiornare una pratica.
    def patch(self, request: Request, pratica_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            pratiche_service.aggiorna_pratica(pratica_id, dict(payload))
            return {"status": "ok"}

        return handle_post_json(request, handler=_handler)
```

### Quando usare `handle_post_json` vs `request.data`

| Metodo | Protocollo | Motivo |
| --- | --- | --- |
| **POST** (create, azioni) | `handle_post_json` | Parsing JSON raw, supporto idempotency, error envelope uniforme |
| **PATCH/PUT** (update, replace) | `request.data` diretto | DRF ha gia' parsato il body; `handle_post_json` chiama `json.loads()` su body raw che in PATCH puo' essere gia' consumato da DRF, causando errori nei test |

Esempio PATCH corretto (pattern adottato):

```python
class UtentiDetailView(AdminAPIView):
    def patch(self, request, auth_user_id):
        result = AmmSoftwareService().update_utente(auth_user_id, request.data)
        return success_response(result)
```

La view resta sottile (una riga). L'error handling e' garantito dal service
(`ServiceError`) e dal middleware (`ApiExceptionMiddleware`), non serve il
wrapper `handle_post_json`.

**Eccezione**: se il PATCH richiede `Idempotency-Key` (operazione critica),
usare `handle_post_json` con `require_idempotency_key=True`.

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
    "retryable": false
  },
  "meta": { "request_id": "uuid-..." }
}
```

| Campo               | Sempre presente | Note                                                                |
| ------------------- | --------------- | ------------------------------------------------------------------- |
| `code`              | si`             | Codice errore strutturato (es. `E_PRATICA_NOT_FOUND`)               |
| `message`           | si`             | Messaggio business-safe, visibile all'utente finale                 |
| `detail`            | no              | Dettaglio tecnico aggiuntivo                                        |
| `technical_message` | no              | Solo se `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1` (mai in produzione) |
| `retryable`         | no              | `true` se il client puo` riprovare la stessa richiesta              |

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

---

## Routing

### Versioning

Tutte le API canoniche sotto `/api/v1/*`. Le route legacy sono disabilitate di default
(`DJANGO_API_LEGACY_ROUTES_ENABLED=0`).

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

### Endpoint attivi (marzo 2026)

**Vendite** (`/api/v1/vendite/`)

| Metodo | Path                                   | Scopo                        |
| ------ | -------------------------------------- | ---------------------------- |
| GET    | `lotti/`                               | Elenco lotti fatturazione    |
| POST   | `pipeline/run/`                        | Avvia pipeline lotto         |
| GET    | `lotti/{id}/fatture/`                  | Fatture di un lotto          |
| GET    | `lotti/{id}/segnalazioni/`             | Riepilogo segnalazioni lotto |
| GET    | `lotti/{id}/task-runs/`                | Task run runtime lotto       |
| POST   | `lotti/{id}/reset-draft/`              | Reset lotto a DRAFT          |
| POST   | `lotti/{id}/fatture/{id}/reset-draft/` | Reset singola fattura        |
| POST   | `commesse/push/run/`                   | Avvia push commesse          |
| GET    | `commesse/push/{id}/`                  | Dettaglio push log           |
| GET    | `commesse/{id}/stato/`                 | Stato commessa               |
| GET    | `commesse/{id}/attivita/`              | Attivita` commessa           |

**Pratiche** (`/api/v1/pratiche/`)

| Metodo | Path                                    | Scopo                              |
| ------ | --------------------------------------- | ---------------------------------- |
| GET    | `/` (root)                              | Elenco pratiche                    |
| POST   | `/` (root)                              | Crea pratica                       |
| GET    | `{id}/`                                 | Dettaglio pratica                  |
| PATCH  | `{id}/`                                 | Aggiorna pratica                   |
| POST   | `{id}/stato/`                           | Cambia stato pratica               |
| POST   | `{id}/assegnazione/`                    | Assegna pratica                    |
| GET    | `{id}/giornale/`                        | Giornale pratica                   |
| POST   | `{id}/sospendi/`                        | Sospendi pratica                   |
| POST   | `{id}/riattiva/`                        | Riattiva pratica                   |
| GET    | `{id}/sospensioni/`                     | Elenco sospensioni                 |
| GET    | `{id}/calcoli-tempo/`                   | Calcoli tempo pratica              |
| GET    | `{id}/flussi/`                          | Elenco flussi                      |
| POST   | `{id}/flussi/`                          | Crea flusso                        |
| GET    | `{id}/flussi/{fid}/`                    | Dettaglio flusso                   |
| POST   | `{id}/flussi/{fid}/stato/`              | Cambia stato flusso                |
| GET    | `{id}/flussi/{fid}/prerequisiti/`       | Prerequisiti flusso                |
| GET    | `{id}/flussi/{fid}/canali/`             | Canali flusso                      |
| GET    | `{id}/flussi/{fid}/regole-generazione/` | Regole generazione                 |
| POST   | `{id}/flussi/{fid}/genera/`             | Genera pratica da flusso           |
| GET    | `{id}/flussi/{fid}/pratiche-generate/`  | Pratiche generate                  |
| POST   | `{id}/flussi/{fid}/sospendi/`           | Sospendi flusso                    |
| POST   | `{id}/flussi/{fid}/riattiva/`           | Riattiva flusso                    |
| GET    | `formule-tempo/`                        | Formule tempo per tipo prestazione |

**Core** (`/api/v1/core/`)

| Metodo | Path                                              | Scopo                                                        |
| ------ | ------------------------------------------------- | ------------------------------------------------------------ |
| GET    | `me/`                                             | Profilo utente corrente                                      |
| GET    | `me/sessioni/`                                    | Sessioni attive                                              |
| POST   | `me/sessioni/{jti}/revoca/`                       | Revoca sessione                                              |
| GET    | `lookup/codici/`                                  | Ricerca codici configurazione                                |
| GET    | `lookup/tipi-ruoli/`                              | Tipi ruolo con visibilita'                                   |
| GET    | `lookup/tipi-ruoli-per-natura/`                   | Tipi ruolo filtrati per natura soggetto                      |
| GET    | `lookup/forme-giuridiche/`                        | Forme giuridiche con policy                                  |
| GET    | `lookup/tipi-soggetto-dettaglio/`                 | Tipi soggetto con nature e policy                            |
| GET    | `lookup/tipi-soggetto-dettaglio/{id}/indirizzi/`  | Matrice indirizzi per tipo                                   |
| GET    | `lookup/comuni/`                                  | Autocomplete comuni                                          |
| GET    | `search/stradario/`                               | Autocomplete stradario per comune                            |
| GET    | `search/stradario-generale/`                      | Autocomplete vie su stradario generale (indice GIN trigram)  |
| GET    | `search/`                                         | Ricerca universale soggetti                                  |
| GET    | `search/{uuid}/detail/`                           | Dettaglio soggetto per ruolo                                 |
| GET    | `users/{id}/permessi-effettivi/`                  | Permessi effettivi utente                                    |
| GET    | `users/{id}/permessi-audit/`                      | Audit permessi utente                                        |
| GET    | `tracciamento/audit-log/`                         | Audit log sistema                                            |
| GET    | `tracciamento/domini-task/`                       | Domini task registrati                                       |
| GET    | `tracciamento/task-registry/`                     | Registry task                                                |
| GET    | `tracciamento/task-implementations/`              | Implementazioni task                                         |
| GET    | `tracciamento/job-runs/`                          | Esecuzioni job                                               |
| GET    | `tracciamento/job-summary/`                       | Riepilogo job                                                |
| GET    | `diagnostics/error-envelope/`                     | Simulazione envelope errore (test)                           |

**Amm. Software** (`/api/v1/amm-software/`) — solo ADMIN
Dettaglio: [api_amm_software.md](api_amm_software.md)

| Metodo | Path                                    | Scopo                          |
| ------ | --------------------------------------- | ------------------------------ |
| GET    | `utenti/`                               | Lista operatori con filtri     |
| POST   | `utenti/`                               | Crea operatore                 |
| GET    | `utenti/{id}/`                          | Dettaglio operatore            |
| PATCH  | `utenti/{id}/`                          | Modifica operatore             |
| POST   | `utenti/{id}/disabilita/`               | Disabilita operatore           |
| GET    | `utenti/{id}/override-aree/`            | Override aree utente           |
| PUT    | `utenti/{id}/override-aree/`            | Sostituisce override aree      |
| GET    | `utenti/{id}/override-azioni/`          | Override azioni utente         |
| PUT    | `utenti/{id}/override-azioni/`          | Sostituisce override azioni    |
| GET    | `utenti/{id}/emittenti-scope/`          | Scope emittenti utente         |
| PUT    | `utenti/{id}/emittenti-scope/`          | Sostituisce scope emittenti    |
| GET    | `reparti/`                              | Lista reparti                  |
| GET    | `reparti/{id}/profilo/`                 | Profilo reparto                |
| PUT    | `reparti/{id}/profilo/`                 | Sostituisce profilo reparto    |
| GET    | `lookup/unita-organizzative/`           | UO per dropdown                |
| GET    | `lookup/aree-funzionali/`              | Aree funzionali per dropdown   |
| GET    | `lookup/azioni-processo/`              | Azioni processo per dropdown   |
| GET    | `lookup/emittenti-fiscali/`            | Emittenti per dropdown         |

**Anagrafiche** (`/api/v1/anagrafiche/`) — gestione geografica e soggetti
Dettaglio: [api_soggetti.md](api_soggetti.md) | [api_indirizzi.md](api_indirizzi.md) | [api_geo_config.md](api_geo_config.md)

| Metodo | Path                    | Scopo                                  |
| ------ | ----------------------- | -------------------------------------- |
| GET    | `indirizzi/`            | Lista indirizzi dettaglio              |
| POST   | `indirizzi/`            | Crea indirizzo (via esistente o nuova) |
| GET    | `indirizzi/{id}/`       | Dettaglio indirizzo                    |
| PATCH  | `indirizzi/{id}/`       | Aggiorna civico/dettagli               |
| GET    | `codici-postali/`       | CAP per comune                         |
| GET    | `toponomastica/`        | Lista toponomastica                    |
| POST   | `toponomastica/`        | Crea tipo strada                       |
| GET    | `toponomastica/{id}/`   | Dettaglio tipo strada                  |
| PATCH  | `toponomastica/{id}/`   | Aggiorna tipo strada                   |
| GET    | `comuni/`               | Lista comuni                           |
| POST   | `comuni/`               | Crea comune                            |
| GET    | `province/`             | Lista province                         |
| POST   | `province/`             | Crea provincia                         |
| GET    | `province/{id}/`        | Dettaglio provincia                    |
| PATCH  | `province/{id}/`        | Aggiorna provincia                     |
| GET    | `province/lookup/`      | Province per dropdown                  |
| GET    | `regioni/`              | Lista regioni                          |
| POST   | `regioni/`              | Crea regione                           |
| GET    | `regioni/{id}/`         | Dettaglio regione                      |
| PATCH  | `regioni/{id}/`         | Aggiorna regione                       |
| GET    | `regioni/lookup/`       | Regioni per dropdown                   |
| GET    | `stati/`                | Lista stati                            |
| POST   | `stati/`                | Crea stato                             |
| GET    | `stati/{id}/`           | Dettaglio stato                        |
| PATCH  | `stati/{id}/`           | Aggiorna stato                         |
| GET    | `stati/lookup/`         | Stati per dropdown                     |

**Auth** (`/api/v1/auth/`)

| Metodo | Path              | Scopo           |
| ------ | ----------------- | --------------- |
| POST   | `token/`          | Login JWT       |
| POST   | `token/refresh/`  | Refresh JWT     |
| POST   | `logout/`         | Logout + revoca |

---

## Autenticazione e autorizzazione

| Aspetto            | Dettaglio                                                                    |
| ------------------ | ---------------------------------------------------------------------------- |
| Protocollo         | JWT Bearer su tutti gli endpoint `/api/v1/*`                                 |
| Token              | `POST /api/v1/auth/token/` — emissione                                       |
| Refresh            | `POST /api/v1/auth/token/refresh/` — rinnovo                                 |
| Permission class   | `ZeroERPPermission` — risoluzione centralizzata                              |
| Superuser          | Bypass totale                                                                |
| Ruolo ADMIN        | Bypass dopo check `ruolo_sistema`                                            |
| Ruolo DISABILITATO | Rifiuto immediato                                                            |
| Azione processo    | Verificata se la view dichiara `post_permission` / `get_permission`          |
| CRUD standard      | Livello area/oggetto (`TUTTO`, `LETTURA`, `BLOCCATO`)                        |
| Scope emittente    | `get_scope_user_id(request)` filtra i dati per emittente fiscale autorizzato |

---

## Decisioni architetturali

### Validazione input

La validazione vive nel **service layer**, tramite helper procedurali:

```python
descrizione = _require_str(payload, "descrizione", "Descrizione obbligatoria.")
sigla = _optional_str(payload, "sigla", "Sigla non puo' essere vuota.")
```

Non si usano serializer DRF ne' Pydantic — gli helper `_require_str`, `_optional_str`,
`optional_int`, `optional_bool` sono sufficienti per il volume attuale.
Rivalutare se i payload distinti superano 20-30.

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

### Tassonomia errori

Tutti i codici errore seguono `E_{MODULO}_{TIPO}` e DEVONO essere registrati
in `error_policies.py` prima dell'uso. Il suffisso determina la categoria:

| Suffisso | HTTP | Esempio |
| --- | --- | --- |
| `_VALIDATION` / `_VALIDAZIONE` | 400 | `E_ANAG_VALIDAZIONE` |
| `_NOT_FOUND` | 404 | `E_PRATICA_NOT_FOUND` |
| `_DUPLICATO` / `_IN_ESECUZIONE` | 409 | `E_ANAG_DUPLICATO` |
| `_NEGATO` / `_DENIED` | 403 | `E_PERMESSO_NEGATO` |

### Test

Test progressivi insieme allo sviluppo, due livelli:

| Livello | Dove | Cosa | DB reale |
| --- | --- | --- | --- |
| Unit test service | `apps/*/tests/services/` | Validazione, dedup, not found, orchestrazione (mock repository) | No |
| Smoke test curl | `backend/scripts/tests/` | Endpoint HTTP reali end-to-end | Si' |

Quando si crea o tocca un service, si scrivono/aggiornano i test corrispondenti.

---

## Checklist nuovo endpoint

1. Creare la view ereditando da `DomainAPIView` (o `AdminAPIView` per amm-software)
2. Definire `area_funzionale` sulla classe
3. List + Create sulla stessa URL: `def get` + `def post`
4. Detail + Update sulla stessa URL: `def get` + `def patch`
5. Per POST/PATCH: usare `handle_post_json` con handler che chiama il **service**
6. Per GET: usare `success_response()` e `paginated_envelope()` per le liste
7. Aggiungere `@extend_schema` con `inline_serializer` per request e response
8. Registrare la route in `urls.py` con name `<dominio>-<risorsa>-list` / `<dominio>-<risorsa>-detail`
9. Scrivere test service in `tests/services/` (validazione, dedup, not found)
10. Se endpoint di ricerca: `is_search_endpoint = True`
11. Registrare i codici errore in `error_policies.py` prima dell'uso
