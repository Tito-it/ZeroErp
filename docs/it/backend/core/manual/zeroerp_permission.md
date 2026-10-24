# ZeroERPPermission (Core Django)

## Scopo

Permission class DRF centrale per ZeroErp. Risolve automaticamente l'area funzionale
dallo schema del model e verifica il livello di accesso tramite `PermissionResolver`.

## Contesto

Classe in `apps/core/api/permissions.py`.
Configurata come default globale DRF in `settings.py`:

```python
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.core.api.permissions.ZeroERPPermission",
    ],
}
```

`DomainAPIView` (`apps/core/api/base_views.py`) la dichiara anche esplicitamente, insieme a
`JwtAuditAuthentication`. Le view che necessitano accesso pubblico (schema, docs, auth)
dichiarano esplicitamente `permission_classes = [AllowAny]` per sovrascrivere il default.
Nello stesso file stanno altre tre permission class, descritte in fondo
(`IsAdminZeroERP`, `PortaleBasePermission`, `ShopBasePermission`).

## Flusso di risoluzione

```text
1. Utente non autenticato?                  → nega (DRF: 401 E_NOT_AUTHENTICATED)
2. is_superuser?                            → OK
3. PermissionResolver.is_super_admin()?     → OK (binding SUPER_ADMIN)
4. ViewSet con <action>_permission?         → check_azione() via PermissionResolver
5. APIView (nessuna action) con <method>_permission? → check_azione()
6. CRUD standard:
   a. Determina required (view/add/change/delete)
   b. Azione sconosciuta (required = None)? → nega (fail-closed)
   c. Risolvi area funzionale
   d. Nessuna area? → OK solo se la view dichiara skip_area_check = True, altrimenti nega
   e. Risolvi livello (oggetto se c'e' un model, altrimenti area)
   f. Verifica required ∈ LIVELLO_MAP[livello]
```

Ogni diniego dopo l'autenticazione diventa un `PermissionDenied` DRF → **403**
`E_PERMISSION_DENIED`.

## Mapping azioni

### ViewSet (usa `view.action`)

| Action          | Tipo CRUD |
|-----------------|-----------|
| `list`          | `view`    |
| `retrieve`      | `view`    |
| `create`        | `add`     |
| `update`        | `change`  |
| `partial_update`| `change`  |
| `destroy`       | `delete`  |

### APIView (usa `request.method`)

| Metodo   | Tipo CRUD |
|----------|-----------|
| `GET`    | `view`    |
| `HEAD`   | `view`    |
| `OPTIONS`| `view`    |
| `POST`   | `add`     |
| `PUT`    | `change`  |
| `PATCH`  | `change`  |
| `DELETE` | `delete`  |

## Attributi view supportati

| Attributo                  | Tipo   | Uso                                               |
|----------------------------|--------|----------------------------------------------------|
| `area_funzionale`          | string | Area forzata quando la view non ha queryset         |
| `<action>_permission`      | string | Codename azione processo per azione ViewSet         |
| `<method>_permission`      | string | Codename azione processo per metodo HTTP (APIView)  |
| `skip_area_check`          | bool   | `True` = ammessa anche senza area funzionale (endpoint utility); senza, una view senza area e' negata |
| `model_permission`         | tuple  | `(app_label, model_name)` per il livello per-oggetto quando la view non ha `queryset` (DomainAPIView con SQL raw) |

Esempio:

```python
class ApiRunLottoPipeline(DomainAPIView):  # JwtAuditAuthentication + ZeroERPPermission
    area_funzionale = "vendite"
    post_permission = "genera_fatture_lotti"
```

## Messaggi di errore specifici

Il diniego porta un **codice**, e il messaggio a video è quello del catalogo per
quel codice. `drf_exception_handler` (`apps/core/api/error_responses.py`) legge
prima il codice dell'**istanza** (`exc.detail.code`, che DRF riempie dal `code`
della permission), poi quello della classe; il messaggio è il `user_message`
della policy di quel codice.

| Causa                                                      | Codice                        |
|------------------------------------------------------------|-------------------------------|
| Azione processo negata                                     | `E_PERMISSION_DENIED`         |
| Azione sconosciuta (fail-closed)                           | `E_PERMISSION_DENIED`         |
| Area non definita (fail-closed)                            | `E_PERMISSION_DENIED`         |
| Livello insufficiente, con profilo                         | `E_PERMISSION_DENIED`         |
| Livello insufficiente, OPERATORE senza profilo per l'area  | `E_REPARTO_SENZA_PROFILO`     |
| Permission «riservate» (admin, portale, shop)              | `E_ACCESSO_RISERVATO_ADMIN` / `_PORTALE` / `_SHOP` |

`ZeroERPPermission` mette `self.code = "E_REPARTO_SENZA_PROFILO"` solo su quel
diniego e lo azzera su ogni altro. Fino al 2026-10-08 il codice dell'istanza non
veniva letto e ogni diniego usciva `E_PERMISSION_DENIED` («Permesso negato.»).

La distinzione "senza profilo" vale solo per il ruolo applicativo OPERATORE (utenti portale e
shop hanno profili legati al ruolo applicativo, non al reparto) e usa
`PermissionResolver.has_profilo_applicabile_per_area()`.

## Fail-closed per azioni sconosciute

Azioni ViewSet non mappate in `ACTION_REQUIRES` e metodi HTTP non mappati in `METHOD_REQUIRES`
vengono **negate per default** (fail-closed). Se una view espone un'azione custom senza dichiarare
l'attributo `<action>_permission`, l'accesso e' negato con log di sicurezza.

## Risoluzione area funzionale

1. Se la view ha un `queryset` con model Django → `PermissionResolver.get_area_schema_db(app_label, model_name)`
2. Altrimenti → attributo `area_funzionale` della view
3. Se nessuna area trovata → **accesso negato** (fail-closed, reason `area_non_definita`),
   salvo che la view dichiari `skip_area_check = True`: solo allora l'endpoint utility senza
   area e' ammesso

Il livello si risolve poi per oggetto (`get_livello_oggetto`) se c'e' un model — dal
`queryset` o, in mancanza, dall'attributo `model_permission` — altrimenti per area
(`get_livello_area`).

## Cache per-request

La cache viene creata/letta su `request._zeroerp_perms_cache` (dict).
Se non esiste ancora, `ZeroERPPermission._get_cache()` la crea caricandola da Redis (L2),
se disponibile e solo col contesto di sessione segnato da `set_jwt_gucs`, e le chiamate
successive nella stessa request la riusano senza query aggiuntive. È l'unico punto che la
carica: nessun middleware la pre-popola (il tentativo in `JwtAuditMiddleware.process_view`
è ritirato con M-1 e S-2 dell'[analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).
Alla fine di ogni `has_permission` (blocco `finally`, anche in caso di diniego) la cache, se
non vuota, viene salvata su Redis per le request successive.

## Security logging

Ogni negazione genera un log `logger.warning("security.permission_denied ...")` con:

- `user_id` — ID utente
- `reason` — tipo di negazione (`azione_negata`, `livello_insufficiente`, `azione_sconosciuta`, `area_non_definita`)

> ⛔ **Il passo «ruolo applicativo = DISABILITATO → nega» e' ritirato** (2026-10-02,
> brief-db-be-fe-area-accessi R-DB-1): una veste spenta tiene il suo tipo e ha
> `attivo = false`, e la tabella rifiuta `DISABILITATO`. Chi ha solo vesti spente
> non ha un'identita' attiva: niente GUC di veste, niente SUPER_ADMIN, e il
> livello d'area nega. Con lui sono usciti `MotivoDiniego.DISABILITATO`, il suo
> messaggio e il ramo gemello di `ShopBasePermission`.
- `path` — endpoint richiesto
- campi aggiuntivi specifici per caso (es. `azione`, `area`, `livello`, `required`)

## Error handling nelle view

Le view API dominio **non devono** usare `try/except Exception` generici.
Le eccezioni non gestite vengono intercettate da `ApiExceptionMiddleware`
(`apps/core/middleware/api_exception_middleware.py`) che le converte nell'envelope
standard del progetto. I service usano `ServiceError` per errori applicativi.

## Altre permission class (`apps/core/api/permissions.py`)

Condividono con `ZeroERPPermission` la cache per-request (`_get_cache`) e il salvataggio su
Redis nel `finally`. Un utente non autenticato e' negato da `IsAdminZeroERP` e
`PortaleBasePermission` (DRF: 401). Anche qui `self.message` non arriva al client (E-5).

| Classe | Usata da | Regola | Diniego |
|---|---|---|---|
| `IsAdminZeroERP` | `AdminAPIView` | superuser Django o `PermissionResolver.is_super_admin()` (binding SUPER_ADMIN, senza passare da profili area/override) | log `security.admin_denied`, messaggio "Accesso riservato agli amministratori." |
| `PortaleBasePermission` | `PortaleAPIView` (`/api/portale/*`) | ruolo applicativo in `RUOLI_PORTALE` (cliente e fornitore portale); nessun controllo di area o livello, lo scope dati e' di RLS + `script.fn_scope_*` | log `security.portale_denied`, messaggio "Accesso riservato agli utenti portale." |
| `ShopBasePermission` | `ShopAPIView` (`/api/shop/*`) | utente anonimo **ammesso** (catalogo pubblico); se autenticato, ruolo applicativo in `RUOLI_SHOP` (`SHOP_CUSTOMER`). Le view che richiedono login verificano `request.user.is_authenticated` da sole | log `security.shop_denied`, messaggio "Accesso riservato ai clienti shop." |

## Dipendenze

- `PermissionResolver` — risoluzione effettiva permessi
- `LIVELLO_MAP` — mapping livello → set azioni CRUD consentite

## Test

`apps/core/tests/api/test_permissions.py` — test unitari con mock del resolver.
