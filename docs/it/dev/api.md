# Linee guida API

> Destinatari: sviluppatori backend di Zero ERP
>
> Vedi anche:
>
> * [Policy ricerca e paginazione](/dev/Policy-ricerca-e-paginazione(API-DB))
> * [Messaggi di errore e log](/guide/Messaggi-di-Errore-e-Generazione-Log)
> * [Guida fatturazione](/guide/fatturazione) — esempio completo di dominio con API

---

## Principi di progettazione

Zero ERP espone **azioni di dominio**, non operazioni CRUD generiche.

| Principio | Regola |
| --- | --- |
| DB-first | Il database e` l'autorita` su stato, vincoli e regole. L'API non replica logica gia` garantita dal DB |
| Azioni atomiche | Ogni endpoint POST rappresenta un'unita` di lavoro completa, eseguita in un'unica transazione |
| Separazione read/write | GET = consultazione (nessun side-effect). POST = comando (modifica stato). PATCH = aggiornamento parziale controllato |
| Nessun CRUD esposto | Non si usano ModelViewSet ne` router DRF automatici. Ogni endpoint e` una APIView esplicita |

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

## Pattern Dual-Class (Base + V1)

Ogni endpoint ha due classi: una base senza autenticazione (utile per test e diagnostica)
e una V1 che aggiunge JWT + permessi.

```python
class ApiRunLottoPipeline(APIView):
    # Scopo: Gestisce la richiesta HTTP POST del relativo endpoint API.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            lotto_id = run_lotto_pipeline(
                lotto_id=optional_int(payload, "lotto_id", zero_as_none=True),
                # ...
            )
            return {"lotto_id": lotto_id, "status": "ok"}

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRunLottoPipelineV1(ApiRunLottoPipeline):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "vendite"
    post_permission = "genera_fatture_lotti"
```

La classe V1 dichiara:

| Attributo | Scopo |
| --- | --- |
| `authentication_classes` | Sempre `[JWTAuthentication]` |
| `permission_classes` | Sempre `[ZeroERPPermission]` |
| `area_funzionale` | Schema DB dell'area (es. `"vendite"`, `"pratiche"`) |
| `post_permission` | Codename azione di processo (opzionale, per comandi specifici) |
| `get_permission` | Idem per GET, se serve restringere la lettura |

La risoluzione permessi segue la catena: superuser bypass -> ruolo_sistema -> azione processo -> livello area/oggetto CRUD. Vedi `apps/core/api/permissions.py`.

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

| Funzione | Scopo |
| --- | --- |
| `optional_int(payload, "key")` | Estrae int o None, errore se non convertibile |
| `optional_bool(payload, "key", default=False)` | Estrae bool con default |
| `optional_iso_date(payload, "key")` | Estrae `date` da stringa ISO |
| `optional_uuid(payload, "key")` | Estrae UUID |

### Idempotency-Key

| Regola | Dettaglio |
| --- | --- |
| Header | `Idempotency-Key` (stringa libera, tipicamente UUID) |
| Obbligatorieta` | `require_idempotency_key=True` su tutti gli endpoint che modificano stato |
| Strong mode | Attivabile con `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1` |
| Store | Tabella `dbops.idempotency_keys` |
| Replay | Key gia` completata: restituisce risposta cached con header `X-Idempotency-Replayed: 1` |
| In-progress | Key gia` in elaborazione: `409` con codice `E_IDEMPOTENCY_IN_PROGRESS` |

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

| Parametro | Default | Max |
| --- | --- | --- |
| `page` | 1 | — |
| `page_size` | 50 | 200 |

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

Il PATCH passa comunque da `handle_post_json` per mantenere parsing e error handling uniformi.

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

| Campo | Sempre presente | Note |
| --- | --- | --- |
| `code` | si` | Codice errore strutturato (es. `E_PRATICA_NOT_FOUND`) |
| `message` | si` | Messaggio business-safe, visibile all'utente finale |
| `detail` | no | Dettaglio tecnico aggiuntivo |
| `technical_message` | no | Solo se `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1` (mai in produzione) |
| `retryable` | no | `true` se il client puo` riprovare la stessa richiesta |

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

| Tipo | Pattern | Esempio |
| --- | --- | --- |
| Lista | `GET /api/v1/<dominio>/` | `GET /api/v1/pratiche/` |
| Dettaglio | `GET /api/v1/<dominio>/<id>/` | `GET /api/v1/pratiche/42/` |
| Azione su entita` | `POST /api/v1/<dominio>/<id>/<azione>/` | `POST /api/v1/pratiche/42/stato/` |
| Azione globale | `POST /api/v1/<dominio>/<azione>/` | `POST /api/v1/vendite/pipeline/run/` |
| Risorsa nested | `GET /api/v1/<dominio>/<id>/<sotto>/` | `GET /api/v1/pratiche/42/flussi/` |
| Azione su nested | `POST /api/v1/<dominio>/<id>/<sotto>/<id>/<azione>/` | `POST /api/v1/pratiche/42/flussi/7/stato/` |

I nomi usano kebab-case: `reset-draft`, `calcoli-tempo`, `regole-generazione`.

### Endpoint attivi (marzo 2026)

**Vendite** (`/api/v1/vendite/`)

| Metodo | Path | Scopo |
| --- | --- | --- |
| GET | `lotti/` | Elenco lotti fatturazione |
| POST | `pipeline/run/` | Avvia pipeline lotto |
| GET | `lotti/{id}/fatture/` | Fatture di un lotto |
| GET | `lotti/{id}/segnalazioni/` | Riepilogo segnalazioni lotto |
| GET | `lotti/{id}/task-runs/` | Task run runtime lotto |
| POST | `lotti/{id}/reset-draft/` | Reset lotto a DRAFT |
| POST | `lotti/{id}/fatture/{id}/reset-draft/` | Reset singola fattura |
| POST | `commesse/push/run/` | Avvia push commesse |
| GET | `commesse/push/{id}/` | Dettaglio push log |
| GET | `commesse/{id}/stato/` | Stato commessa |
| GET | `commesse/{id}/attivita/` | Attivita` commessa |

**Pratiche** (`/api/v1/pratiche/`)

| Metodo | Path | Scopo |
| --- | --- | --- |
| GET | `/` (root) | Elenco pratiche |
| POST | `/` (root) | Crea pratica |
| GET | `{id}/` | Dettaglio pratica |
| PATCH | `{id}/` | Aggiorna pratica |
| POST | `{id}/stato/` | Cambia stato pratica |
| POST | `{id}/assegnazione/` | Assegna pratica |
| GET | `{id}/giornale/` | Giornale pratica |
| POST | `{id}/sospendi/` | Sospendi pratica |
| POST | `{id}/riattiva/` | Riattiva pratica |
| GET | `{id}/sospensioni/` | Elenco sospensioni |
| GET | `{id}/calcoli-tempo/` | Calcoli tempo pratica |
| GET | `{id}/flussi/` | Elenco flussi |
| POST | `{id}/flussi/` | Crea flusso |
| GET | `{id}/flussi/{fid}/` | Dettaglio flusso |
| POST | `{id}/flussi/{fid}/stato/` | Cambia stato flusso |
| GET | `{id}/flussi/{fid}/prerequisiti/` | Prerequisiti flusso |
| GET | `{id}/flussi/{fid}/canali/` | Canali flusso |
| GET | `{id}/flussi/{fid}/regole-generazione/` | Regole generazione |
| POST | `{id}/flussi/{fid}/genera/` | Genera pratica da flusso |
| GET | `{id}/flussi/{fid}/pratiche-generate/` | Pratiche generate |
| POST | `{id}/flussi/{fid}/sospendi/` | Sospendi flusso |
| POST | `{id}/flussi/{fid}/riattiva/` | Riattiva flusso |
| GET | `formule-tempo/` | Formule tempo per tipo prestazione |

**Core** (`/api/v1/core/`)

| Metodo | Path | Scopo |
| --- | --- | --- |
| GET | `lookup/codici/` | Ricerca codici configurazione |
| GET | `users/{id}/permessi-effettivi/` | Permessi effettivi utente |
| GET | `users/{id}/permessi-audit/` | Audit permessi utente |
| GET | `tracciamento/audit-log/` | Audit log sistema |
| GET | `tracciamento/domini-task/` | Domini task registrati |
| GET | `tracciamento/task-registry/` | Registry task |
| GET | `tracciamento/task-implementations/` | Implementazioni task |
| GET | `tracciamento/job-runs/` | Esecuzioni job |
| GET | `tracciamento/job-summary/` | Riepilogo job |

---

## Autenticazione e autorizzazione

| Aspetto | Dettaglio |
| --- | --- |
| Protocollo | JWT Bearer su tutti gli endpoint `/api/v1/*` |
| Token | `POST /api/v1/auth/token/` — emissione |
| Refresh | `POST /api/v1/auth/token/refresh/` — rinnovo |
| Permission class | `ZeroERPPermission` — risoluzione centralizzata |
| Superuser | Bypass totale |
| Ruolo ADMIN | Bypass dopo check `ruolo_sistema` |
| Ruolo DISABILITATO | Rifiuto immediato |
| Azione processo | Verificata se la view dichiara `post_permission` / `get_permission` |
| CRUD standard | Livello area/oggetto (`TUTTO`, `LETTURA`, `BLOCCATO`) |
| Scope emittente | `get_scope_user_id(request)` filtra i dati per emittente fiscale autorizzato |

---

## Checklist nuovo endpoint

1. Creare la classe base `ApiXxx(APIView)` in `apps/<dominio>/api/views.py`
2. Creare la classe `ApiXxxV1(ApiXxx)` con auth, permission e `area_funzionale`
3. Per POST: usare `handle_post_json` con handler interno e `require_idempotency_key=True`
4. Per GET: usare `success_response()` e `get_scope_user_id(request)` se serve scope emittente
5. Aggiungere `@extend_schema` con `inline_serializer` per request e response
6. Registrare la route in `urls_v1.py` con name `<dominio>-v1-<nome>`
7. Scrivere test in `tests/api/`
8. Se l'endpoint e` di ricerca: `is_search_endpoint = True` sulla classe base
