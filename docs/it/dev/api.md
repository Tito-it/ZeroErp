# Linee guida API

> Destinatari: sviluppatori backend di Zero ERP
> Aggiornato: 15 marzo 2026
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

Un'unica API, parametro `rel` con whitelist (83 tabelle su 9 schemi, 2026-07-02).
Restituisce sempre `id, codice, codice_interno, descrizione, attivo, codice_stabile`
con paginazione e search. Variante **specializzata** (config `_LOOKUP_SPECIALIZZATE`):
stessa API e contratto + UNA colonna extra per relazione (es.
`pratiche.tipi_prestazione` → `categoria`, `catalogo.unita_misura` → `tipo_uom_id`)
— preferirla a un endpoint dedicato quando serve un solo campo in piu'.
Dettagli: `docs/it/backend/core/manual/api_lookup_codici.md`.

**2. Lookup dedicato** — quando servono JOIN o campi extra non riducibili a `id, codice, descrizione`:

```text
GET /api/v1/anagrafiche/province/lookup/     → sigla + regione_descrizione
GET /api/v1/anagrafiche/regioni/lookup/      → stato_descrizione
GET /api/v1/anagrafiche/stati/lookup/        → codice_iso2
```

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

# Per endpoint del portale clienti/fornitori (/api/portale/*)
class PortaleFattureListView(PortaleAPIView):
    def get(self, request): ...

# Per endpoint del negozio online (/api/shop/*, anche pubblici)
class ShopCatalogoView(ShopAPIView):
    def get(self, request): ...
```

| Base class | Auth | Permessi | Uso |
| --- | --- | --- | --- |
| `DomainAPIView` | JWT | `ZeroERPPermission` + `area_funzionale` | Endpoint di dominio |
| `AdminAPIView` | JWT | `IsAdminZeroERP` (check binding `SUPER_ADMIN`) | Amm. Software |
| `PortaleAPIView` | JWT | `PortaleBasePermission` (`ruolo_applicativo ∈ {CLIENTE_PORTALE, FORNITORE_PORTALE}`) | Portale clienti/fornitori |
| `ShopAPIView` | JWT opzionale | `ShopBasePermission` (anonimo oppure `SHOP_CUSTOMER`) | Negozio online |

### Attributi di classe

| Attributo | Scopo | Obbligatorio |
| --- | --- | --- |
| `area_funzionale` | Schema DB dell'area (es. `"vendite"`, `"anagrafiche"`) | Si' su DomainAPIView |
| `is_search_endpoint` | Abilita `SearchBurstRateThrottle` | No |
| `post_permission` | Codename azione di processo (per comandi specifici) | No |
| `skip_area_check` | Salta il check area — ammesso solo per endpoint cross-dominio (profilo, sessioni, lookup) | No |

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

La risoluzione permessi segue la catena: superuser bypass → `ruolo_applicativo = DISABILITATO` → bypass `SUPER_ADMIN` → azione processo → livello area/oggetto CRUD. Vedi `apps/core/api/permissions.py`.

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

### Query params (filtri lista)

I filtri opzionali da query string si normalizzano con gli helper di
`apps.core.api.payload_validators` (passati **per valore**, es.
`qp_bool_optional(qp.get("attivo"), "attivo")`):

| Funzione                            | Scopo                                                                                  |
| ----------------------------------- | -------------------------------------------------------------------------------------- |
| `qp_str(raw)`                       | stringa o `None` se assente/vuota (strip)                                               |
| `qp_int(raw, default)`              | int con default; fallback silenzioso al default se non numerico                        |
| `qp_int_strict(raw, name, default)` | int con default; **400** se presente ma non numerico                                   |
| `qp_int_optional(raw, name)`        | int **opzionale strict**: `None` se assente/vuoto, **400** se non numerico             |
| `qp_bool(raw, default=True)`        | bool con default (False solo su `0/false/no/n/off`)                                     |
| `qp_bool_optional(raw, name)`       | bool **opzionale strict**: `None` se assente/vuoto, `True/False` sui token, **400** se non riconosciuto |
| `qp_iso_date_optional(raw, name)`   | `date` **opzionale strict**: `None` se assente/vuoto, **400** se malformata             |
| `parse_list_params(qp, *, default_limit, max_limit, default_order)` | bundle `search/limit/offset/order_by/order_dir/page` per liste **offset-based** |

**Contratto degli helper `*_optional` (dal 2026-06-04):**

* **valore vuoto** (`?attivo=`) ⇒ trattato come **assente** → `None` (nessun filtro).
  Per omettere un filtro è equivalente non inviare la chiave.
* **valore non riconosciuto / non valido** (`?attivo=banana`, `?utility_id=abc`) ⇒
  **`400` `E_VALIDATION_INPUT`** (niente coercion silenziosa: prima alcuni filtri
  bool accettavano il garbage come `True`/`False`).
* token bool riconosciuti: `1/true/yes/y/on` → `True`, `0/false/no/n/off` → `False`.

> **Paginazione page-based** (`page`/`page_size`, alternativa a `limit`/`offset`):
> validala nel service con
> `validate_pagination(page, page_size, *, error_code, function_name)`
> (`apps.core.services.list_helpers`), che valida e ritorna l'offset. Per
> l'ordinamento: `validate_order_params(order_by, order_dir, *, allowed_columns, error_code, function_name)`.

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

### Namespace per tipo di utente (multi-face auth)

Il refactor multi-face auth (WIP `sviluppo-multi-face-auth.md`) introduce
la distinzione formale tra namespace per tipo di consumatore:

| Namespace | Base view | Chi accede | Stato |
| --- | --- | --- | --- |
| `/api/v1/<dominio>/` | `DomainAPIView` / `AdminAPIView` | Operatori interni (dipendenti, ruolo_applicativo=OPERATORE) | **Attivo** |
| `/api/v1/portale/` | `PortaleAPIView` | Clienti e fornitori del portale | **Attivo** (auth+invito+attivazione, MVP dati Stage C) |
| `/api/v1/shop/` | `ShopAPIView` | Negozio online (pubblico + SHOP_CUSTOMER) | **Attivo** (auth+invito+attivazione admin-driven; catalogo/checkout Stage D) |

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

Per l'inventario completo degli endpoint attivi per dominio, consultare la documentazione OpenAPI generata automaticamente all'endpoint `/api/docs/` oppure i documenti manuali per dominio:

* **Pratiche**: [api_pratiche_list.md](/backend/pratiche/manual/api_pratiche_list) | [api_pratiche_generate.md](/backend/pratiche/manual/api_pratiche_generate) | [api_pratiche_note.md](/backend/pratiche/manual/api_pratiche_note) | [api_pratiche_allegati.md](/backend/pratiche/manual/api_pratiche_allegati) | [api_flusso_assegnazione.md](/backend/pratiche/manual/api_flusso_assegnazione) | [api_operatori_reparto.md](/backend/pratiche/manual/api_operatori_reparto) | [api_prendi_in_carico.md](/backend/pratiche/manual/api_prendi_in_carico) | [api_coda_lavoro.md](/backend/pratiche/manual/api_coda_lavoro)
* **Amm. Software**: [api_amm_software.md](../backend/amm-software/manual/api_amm_software.md)
* **Anagrafiche**: [api_soggetti.md](../backend/anagrafiche/manual/api_soggetti.md) | [api_indirizzi.md](../backend/anagrafiche/manual/api_indirizzi.md) | [api_geo_config.md](../backend/anagrafiche/manual/api_geo_config.md) | [api_fornitori.md](../backend/anagrafiche/manual/api_fornitori.md)
* **Auth**: [api_multi_veste_token.md](/backend/core/manual/api_multi_veste_token) | [auth_views_audit.md](/backend/core/manual/auth_views_audit) | [api_user_profile.md](/backend/core/manual/api_user_profile) | [api_token_cambio_password.md](/backend/core/manual/api_token_cambio_password) | [api_password_reset.md](/backend/core/manual/api_password_reset) | [api_invito_operatore.md](/backend/core/manual/api_invito_operatore) | [api_invito_portale_shop.md](/backend/core/manual/api_invito_portale_shop) | [api_logout.md](/backend/core/manual/api_logout)
* **Email**: [api_email.md](/backend/core/manual/api_email)
* **Parametri**: [api_parameter_settings.md](../backend/core/manual/api_parameter_settings.md)
* **Vendite — Pricing v5**: [api_preventivi.md](/backend/vendite/manual/api_preventivi) | [api_listini.md](/backend/vendite/manual/api_listini) | [api_contratti.md](/backend/vendite/manual/api_contratti) | [api_promo_articoli.md](/backend/vendite/manual/api_promo_articoli) | [api_pricing.md](/backend/vendite/manual/api_pricing) | [api_approvazioni_prezzo.md](/backend/vendite/manual/api_approvazioni_prezzo) | [api_vendite_lookups.md](/backend/vendite/manual/api_vendite_lookups) | [api_vendite_form_defaults.md](/backend/vendite/manual/api_vendite_form_defaults)
* **Vendite — Ciclo attivo**: [api_offerte.md](/backend/vendite/manual/api_offerte) | [api_ordini.md](/backend/vendite/manual/api_ordini)
* **Vendite — Situazione aperta**: [api_dashboard_aperto.md](/backend/vendite/manual/api_dashboard_aperto) — stock documenti per `area × fase` senza asse temporale + drill-down (read-only su `vw_dash_aperto_*`; sostituisce la dashboard 5-card, Fase 3 due-lenti)
* **Vendite — Dashboard competenza (Lente 1)**: [api_dashboard_competenza.md](/backend/vendite/manual/api_dashboard_competenza) — funnel commessa→fattura per mese di competenza: aggregata 12 mesi × 4 stadi + breakdown stato fattura, drill-down attività, errori vivi (read-only su `vw_dash_competenza_*`)
* **Vendite — Dashboard backlog (Lente 2)**: [api_dashboard_backlog.md](/backend/vendite/manual/api_dashboard_backlog) — non-collegati per anzianità + classe di azionabilità: contatori 🟠/🔵/🔴 + lista con motivo/azione (read-only su `vw_dash_backlog_*` + lookup `config.motivi_fermo`)
* **Documenti**: [api_documenti_templates.md](/backend/documenti/manual/api_documenti_templates) — read-only v1 motore documentale (lista/dettaglio template + versioni). Building block trasversali per view "per sorgente" (offerta/preventivo/contratto): [api_documenti_helpers.md](/backend/documenti/manual/api_documenti_helpers) — `resolve_contesto_documentale` + `extract_allegati` (2026-05-28).
* **UI — Personalizzazioni liste (runtime)**: [api_ui_liste.md](/backend/ui/manual/api_ui_liste) — risoluzione configurazione lista, catalogo modale, UPSERT/DELETE preferenza utente. Meta-API trasversale (`skip_area_check=True`).
* **UI — Personalizzazioni liste (admin Blocco F)**: [api_ui_admin_personalizzazioni.md](/backend/ui/manual/api_ui_admin_personalizzazioni) — Fase 1: CRUD preset (testata + composizione atomica) + UPSERT/DELETE permessi colonna; auth via azioni di processo `ui_preset_manage`/`ui_permesso_manage` o SUPER_ADMIN. Fase 2 (DEF-5b 2026-05-10): CRUD `ui.lista_definizione` + `ui.lista_colonna` SUPER_ADMIN-only via `AdminAPIView`.
* **UI — Export liste (DEF-1, 2026-05-10)**: endpoint dedicato per dominio (`GET /api/v1/anagrafiche/clienti/export/?formato=csv|xlsx`, `GET /api/v1/anagrafiche/soggetti/export/?formato=csv|xlsx` dal 2026-05-11, `GET /api/v1/anagrafiche/fornitori/export/?formato=csv|xlsx` dal 2026-05-24, `GET /api/v1/vendite/contratti/export/?formato=csv|xlsx` dal 2026-06-02; estensione altre liste in DEF-8). Renderer puro generico `apps.ui.services.lista_export_service.ListaExportService` no-fetch: riceve righe + config colonne + filtri applicati, produce bytes CSV (BOM UTF-8 + header `#` JSON filtri) o XLSX (foglio "Dati" + foglio "Filtri applicati", styling header bold). Hard cap 10.000 righe, errori `E_UI_EXPORT_LIMIT_EXCEEDED` (422) / `E_UI_EXPORT_FORMAT_INVALID` (400) / `E_UI_EXPORT_FAILED` (500). Niente SQL dinamico sulla `vista_sql`: ogni dominio chiama il proprio repository esistente e delega al renderer. **Coda invariante estratta** (regola del 2, 2026-06-02) in `apps.ui.api.export_helpers.{parse_export_format,build_export_response}`: ogni view export mantiene solo il parsing dei propri filtri + la chiamata al service con `limit=EXPORT_MAX_ROWS+1`; validazione formato, guard limite, risoluzione colonne dalla config runtime, render e `HttpResponse` vivono nel building block.

Per i building block backend riutilizzabili (helpers, services, repository), consultare il [Catalogo Building Block Backend](backend/catalogo-building-block-backend.md).

---

## Autenticazione e autorizzazione

| Aspetto            | Dettaglio                                                                    |
| ------------------ | ---------------------------------------------------------------------------- |
| Protocollo         | JWT Bearer su tutti gli endpoint `/api/v1/*`                                 |
| Token login        | 3 endpoint namespace-specific (admin/portale/shop), vedi sezione sotto       |
| Token refresh      | 3 endpoint namespace-specific con guard cross-veste                          |
| JWT claim custom   | `identita_id` + `ruolo_applicativo` + `sid` (session id stabile)             |
| Permission class   | `ZeroERPPermission` — risoluzione centralizzata                              |
| Superuser          | Bypass totale                                                                |
| SUPER_ADMIN        | Bypass via `script.fn_is_super_admin` (filtro veste OPERATORE, §8.3.7)       |
| DISABILITATO       | Rifiuto immediato su `ruolo_applicativo = DISABILITATO`                      |
| Azione processo    | Verificata se la view dichiara `post_permission` / `get_permission`          |
| CRUD standard      | Livello area/oggetto (`TUTTO`, `LETTURA`, `BLOCCATO`)                        |
| Scope emittente    | Filtra i dati per emittente fiscale autorizzato (vedi sotto)                 |

### Endpoint login/refresh multi-veste (§8.3 PR-B1)

Post refactor multi-face auth, ogni namespace ha i propri endpoint di login
e refresh che ammettono solo il subset di vesti che gli compete:

| Path login | Path refresh | Vesti ammesse |
| --- | --- | --- |
| `POST /api/v1/admin/token/` | `POST /api/v1/admin/token/refresh/` | `OPERATORE` |
| `POST /api/v1/portale/token/` | `POST /api/v1/portale/token/refresh/` | `CLIENTE_PORTALE`, `FORNITORE_PORTALE` |
| `POST /api/v1/shop/token/` | `POST /api/v1/shop/token/refresh/` | `SHOP_CUSTOMER` |

Il vecchio path unificato `/api/v1/auth/token/` e' stato **rimosso senza
alias** (breaking, grace 0). Client pre-refactor devono aggiornarsi.

Contratto HTTP completo, claim JWT, codici errore e guard cross-namespace:
[api_multi_veste_token.md](../backend/core/manual/api_multi_veste_token.md).

### Identita utente: `ruolo_applicativo` e `SUPER_ADMIN`

Il vecchio enum `ruolo_sistema` (ADMIN / OPERATIVO / DISABILITATO) e'
stato sostituito dal refactor multi-face auth con:

* `ruolo_applicativo` — categoria dell'identita' digitale
  (`OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`,
  `API_CLIENT`, `DISABILITATO`). Letto via
  `PermissionResolver.get_ruolo_applicativo(user)` (GUC-first).
* `SUPER_ADMIN` — privilegio di bypass totale, bindato sulla singola
  identita' via `config.profili_accesso_bindings` (profilo id 9100).
  Letto via `PermissionResolver.is_super_admin(user)`.

La mapping legacy ricostruito da `/permessi-effettivi/`:
`SUPER_ADMIN -> "ADMIN"`; `ruolo_applicativo=DISABILITATO -> "DISABILITATO"`;
altrimenti `-> "OPERATIVO"`.

### Propagazione identita' al DB (GUC)

Al login e su ogni request JWT, `JwtAuditAuthentication` propaga
5 GUC di sessione PostgreSQL per audit e RLS:

| GUC | Valore |
| --- | --- |
| `app.jwt_user` | username Django |
| `app.current_user_id` | `auth_user.id` |
| `app.current_identita_id` | `identita_digitali.id` dell'identita attiva |
| `app.ruolo_applicativo` | `OPERATORE` / `CLIENTE_PORTALE` / ... |
| `app.soggetto_ruolo_id` | `soggetti_ruoli.id` dell'identita' |

Invariante "tutto o niente": i 3 GUC di identita' sono popolati insieme
o restano stringa vuota. Vedi
`docs/it/guide/risorse-umane-e-accessi.md` sezione GUC.

**Reset per-richiesta (anti-leak).** `JwtAuditMiddleware.process_request`
azzera i 5 GUC all'**inizio** di ogni richiesta `/api/`, **prima** che
l'auth class li ripopoli e prima di qualunque query. È **incondizionato**
(anche richieste anonime) e **fail-closed**: se il reset fallisce la
richiesta NON viene servita (500 `E_GUC_RESET_FAILED`). Chiude il leak
cross-request sulle connessioni persistenti (`CONN_MAX_AGE > 0` / pooling),
critico ora che la RLS filtra in base ai GUC. Vedi
`docs/it/dev/work-done/analisi-attivazione-rls-operatori-be-fe.md` §1.

### Scope emittente

Due pattern disponibili in base al dominio:

1. **Vendite** — `get_scope_user_id(request)` passa `auth_user_id` alle funzioni SQL
   che risolvono lo scope internamente via `fn_get_emittenti_scope_sr_ids`.
2. **Search / Anagrafiche** — `PermissionResolver.get_emittenti_sr_ids(request.user)`
   risolve in Python i `soggetto_ruolo_id` degli emittenti autorizzati e li passa
   come array `bigint[]` alle query SQL.

Usare `get_emittenti_sr_ids` (filtra su `*_soggetto_ruolo_id`, convenzione SR)
o `get_emittenti_pk_ids` (filtra su `emittente_fiscale_id` PK) secondo la colonna.
`get_emittenti_ids` è ora un **alias guarded di `get_emittenti_pk_ids`** (stessa
convenzione PK + bypass SUPER_ADMIN + fail-closed su identita non attiva): usare
i nomi espliciti `_sr_ids`/`_pk_ids` per chiarezza di convenzione.

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

Vedi `docs/it/dev/work-done/analisi-attivazione-rls-operatori.md`.

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

### Atomicità e composizione di scritture

Un endpoint che modifica stato è **un'unità di lavoro atomica**. Quando l'operazione compone
**più scritture** (INSERT/UPDATE o `SELECT fn_...` di mutazione), decidere **dove** vive la
transazione — non lasciarle in autocommit una dietro l'altra (se la 2ª fallisce, la 1ª resta
committata → stato parziale / orfani).

| L'operazione... | Meccanismo |
| --- | --- |
| compone **solo** scritture/fn DB | **una sola `SELECT fn_madre(...)`** nel repository — atomica per costruzione (preferito, DB-first) |
| richiede orchestrazione **Python** (lock, dispatch handler, control-flow) | **`with transaction.atomic()`** esplicito nel service |
| ha un **side-effect esterno** (email/SMTP) | pattern **outbox/saga**, mai dentro la transazione |

> ⚠️ **Non affidarsi a `ATOMIC_REQUESTS`.** Sarebbe inefficace qui: `handle_post_json` **cattura**
> l'eccezione e restituisce una `Response`, quindi non esce mai dalla view → il rollback a livello
> di request non scatta e il parziale viene committato (e su `IntegrityError` il 4xx diventa 500).
> **`with transaction.atomic()` esplicito è invece sicuro**: fa rollback al confine del blocco (nel
> suo `__exit__`), *prima* che `handle_post_json` catturi l'eccezione. È l'attrezzo corretto.

**Guardrail: «una azione = una unità atomica».** Un metodo service che compone 2+ scritture con
side-effect **deve** avvolgerle in un solo `transaction.atomic()` **oppure** delegare a una singola
funzione madre DB. Domini con natura mista (es. pratiche): le operazioni pure-dato → madre DB
(`pratiche.fn_crea_pratica`); il motore-flussi-con-handler → `transaction.atomic()`.

> Faccia DB della stessa regola (come scrivere la funzione madre): [linee-guida-sql §5b](/linee-guida-sql).
> Caso di studio, criterio esteso e catalogo dei finding:
> [analisi-fix-transazioni](/dev/work-in-progress/analisi-fix-transazioni).

### Tassonomia errori

Tutti i codici errore seguono `E_{MODULO}_{TIPO}` e DEVONO essere registrati
in `error_policies.py` prima dell'uso. Il suffisso determina la categoria:

| Suffisso | HTTP | Esempio |
| --- | --- | --- |
| `_VALIDATION` / `_VALIDAZIONE` | 400 | `E_ANAG_VALIDAZIONE` |
| `_NOT_FOUND` | 404 | `E_PRATICA_NOT_FOUND` |
| `_DUPLICATO` / `_IN_ESECUZIONE` | 409 | `E_ANAG_DUPLICATO` |
| `_NEGATO` / `_DENIED` | 403 | `E_PERMESSO_NEGATO` |

**Eccezione — codici middleware-level.** Alcune risposte sono costruite
direttamente da `JwtAuditMiddleware` (helper `_json_error`, stesso envelope)
e **non** passano dall'exception handler / `error_policies.py`:

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_USER_DISABILITATO` | 403 | utente con `ruolo_applicativo = DISABILITATO` (rifiuto early) |
| `E_GUC_RESET_FAILED` | 500 | il reset GUC d'inizio richiesta è fallito (fail-closed, vedi §GUC) |
| `E_DB_ROLE_UNSAFE` | 500 | la connessione del percorso richiesta è su un ruolo `BYPASSRLS` (guard fail-open RLS: `DB_USER` misconfigurato sul ruolo batch, o canale di sistema usato per errore nel web → richiesta rifiutata, fail-closed) |

#### Codici auth multi-veste (§8.3 PR-B1)

| Codice | HTTP | UI action | Quando |
| --- | --- | --- | --- |
| `E_VESTE_NON_ATTIVA` | 403 | show_error_banner | Login o refresh su un namespace senza identita con la veste richiesta |
| `E_JWT_SENZA_IDENTITA` | 401 | redirect_login | JWT senza claim `identita_id` (token pre-refactor multi-face) |
| `E_IDENTITA_NON_ATTIVA` | 401 | redirect_login | Claim `identita_id` non corrisponde a identita attiva (revocata dopo emissione) |

Vedi [api_multi_veste_token.md](../backend/core/manual/api_multi_veste_token.md)
per il contratto completo.

#### Codici invito/attivazione portale + shop (§8.4 PR-B2 + §13.7 B1)

| Codice | HTTP | UI action | Quando |
| --- | --- | --- | --- |
| `E_INVITO_PORTALE` | 400 | show_error_banner | Errore admin durante invio/reinvio invito portale o shop (validazione, identita gia' attiva, veste non supportata) |
| `E_ATTIVAZIONE_PORTALE` | 400 | show_error_banner | Errore consume token attivazione portale (token assente/scaduto, password mismatch, identita rimossa) |
| `E_ATTIVAZIONE_SHOP` | 400 | show_error_banner | Errore consume token attivazione shop (simmetrico portale, B1 §13.7) |
| `E_ATTIVAZIONE_SHOP_CROSS` | 400 | show_error_banner | Errore attivazione cross-veste shop dal profilo portale (veste non CLIENTE_PORTALE, identita gia' su altro auth_user, GUC vuota) |

Vedi [api_invito_portale_shop.md](../backend/core/manual/api_invito_portale_shop.md)
per il contratto completo dei flussi invito + attivazione portale e shop.

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

---

## Disattivazione record — ordine UPDATE e trigger

Il database usa trigger `trgfn_prevent_deactivate_if_children` sulle tabelle con
campo `attivo`. Il trigger **impedisce di disattivare un padre se ha figli attivi**.

Questo vale per tutte le relazioni padre-figlio dove entrambi hanno `attivo`:
`risorse_umane` → `risorse_umane_auth_user`, e future relazioni analoghe.

### Regola: disattivare dal basso verso l'alto, riattivare dall'alto verso il basso

**Disattivazione** — prima i figli, poi il padre:

```python
# 1. Disattiva figlio
UPDATE risorse_umane_auth_user SET attivo = false WHERE ...
# 2. Disattiva padre (trigger OK: figlio gia' inattivo)
UPDATE risorse_umane SET attivo = false WHERE ...
```

**Riattivazione** — prima il padre, poi i figli:

```python
# 1. Riattiva padre
UPDATE risorse_umane SET attivo = true WHERE ...
# 2. Riattiva figlio (padre gia' attivo)
UPDATE risorse_umane_auth_user SET attivo = true WHERE ...
```

### Perche'

Il trigger e' una guardia di integrita': un figlio attivo senza padre attivo
non ha senso nel dominio. Se il codice Python non rispetta l'ordine, il trigger
blocca l'operazione con errore `E_ATTIVO_BLOCK_CHILDREN_EXIST`.

Questa regola si applica a **qualsiasi** operazione di disattivazione/riattivazione
nel sistema, non solo agli operatori. Quando si implementa un nuovo endpoint
`disabilita`/`riattiva`, verificare le relazioni padre-figlio e rispettare l'ordine.
