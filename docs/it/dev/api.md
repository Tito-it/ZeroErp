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

Un'unica API, parametro `rel` con whitelist (~45 tabelle config).
Restituisce sempre `id, codice, descrizione` con paginazione e search.

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

* **Pratiche**: [api_pratiche_list.md](/backend/pratiche/manual/api_pratiche_list) | [api_pratiche_generate.md](/backend/pratiche/manual/api_pratiche_generate) | [api_pratiche_note.md](/backend/pratiche/manual/api_pratiche_note) | [api_pratiche_allegati.md](/backend/pratiche/manual/api_pratiche_allegati)
* **Amm. Software**: [api_amm_software.md](api_amm_software.md)
* **Anagrafiche**: [api_soggetti.md](api_soggetti.md) | [api_indirizzi.md](api_indirizzi.md) | [api_geo_config.md](api_geo_config.md) | [api_fornitori.md](api_fornitori.md)
* **Auth**: [api_multi_veste_token.md](/backend/core/manual/api_multi_veste_token) | [auth_views_audit.md](/backend/core/manual/auth_views_audit) | [api_user_profile.md](/backend/core/manual/api_user_profile) | [api_token_cambio_password.md](/backend/core/manual/api_token_cambio_password) | [api_password_reset.md](/backend/core/manual/api_password_reset) | [api_invito_operatore.md](/backend/core/manual/api_invito_operatore) | [api_invito_portale_shop.md](/backend/core/manual/api_invito_portale_shop) | [api_logout.md](/backend/core/manual/api_logout)
* **Email**: [api_email.md](/backend/core/manual/api_email)
* **Parametri**: [api_parameter_settings.md](../backend/core/manual/api_parameter_settings.md)
* **Vendite — Pricing v5**: [api_preventivi.md](/backend/vendite/manual/api_preventivi) | [api_listini.md](/backend/vendite/manual/api_listini) | [api_contratti.md](/backend/vendite/manual/api_contratti) | [api_promo_articoli.md](/backend/vendite/manual/api_promo_articoli) | [api_pricing.md](/backend/vendite/manual/api_pricing) | [api_approvazioni_prezzo.md](/backend/vendite/manual/api_approvazioni_prezzo)

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

### Scope emittente

Due pattern disponibili in base al dominio:

1. **Vendite** — `get_scope_user_id(request)` passa `auth_user_id` alle funzioni SQL
   che risolvono lo scope internamente via `fn_get_emittenti_scope_sr_ids`.
2. **Search / Anagrafiche** — `PermissionResolver.get_emittenti_sr_ids(request.user)`
   risolve in Python i `soggetto_ruolo_id` degli emittenti autorizzati e li passa
   come array `bigint[]` alle query SQL.

Usare `get_emittenti_sr_ids` (non `get_emittenti_ids`) quando il SQL filtra su
`emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id`.
`get_emittenti_ids` ritorna le PK di `emittenti_fiscali.id`, utili solo per
lookup diretti sulla tabella emittenti.

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
