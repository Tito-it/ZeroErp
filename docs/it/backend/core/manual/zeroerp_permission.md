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

Le view che necessitano accesso pubblico (schema, docs, auth) dichiarano esplicitamente
`permission_classes = [AllowAny]` per sovrascrivere il default.

## Flusso di risoluzione

```text
1. Utente non autenticato?          → 403
2. is_superuser?                    → OK
3. ruolo_sistema = DISABILITATO?    → 403 "Utente disabilitato"
4. ruolo_sistema = ADMIN?           → OK
5. Azione custom dichiarata?        → check_azione() via PermissionResolver
6. CRUD standard:
   a. Determina required (view/add/change/delete)
   b. Risolvi area funzionale
   c. Risolvi livello (oggetto o area)
   d. Verifica required ∈ LIVELLO_MAP[livello]
```

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

Esempio:

```python
class ApiRunLottoPipelineV1(ApiRunLottoPipeline):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "vendite"
    post_permission = "genera_fatture_lotti"
```

## Messaggi di errore specifici

La permission class imposta `self.message` con messaggi differenziati:

| Causa                              | Messaggio                                                       |
|-------------------------------------|-----------------------------------------------------------------|
| `ruolo_sistema = DISABILITATO`     | "Utente disabilitato. Contattare l'amministratore."             |
| Azione processo negata              | "Non hai i permessi per questa operazione."                     |
| BLOCCATO con profilo reparto        | "Non hai i permessi per questa operazione."                     |
| BLOCCATO senza profilo reparto      | "Il reparto non ha ancora un profilo permessi configurato."     |

La distinzione "senza profilo" usa `PermissionResolver.has_profilo_reparto_area()` per guidare
l'utente verso la configurazione corretta del reparto.

## Risoluzione area funzionale

1. Se la view ha un `queryset` con model Django → `PermissionResolver.get_area_schema_db(app_label, model_name)`
2. Altrimenti → attributo `area_funzionale` della view
3. Se nessuna area trovata → accesso consentito (endpoint utility senza area)

## Cache per-request

La cache viene creata/letta su `request._zeroerp_perms_cache` (dict).
Evita query duplicate quando piu' permission check avvengono nella stessa request.

## Dipendenze

- `PermissionResolver` — risoluzione effettiva permessi
- `LIVELLO_MAP` — mapping livello → set azioni CRUD consentite

## Test

`apps/core/tests/api/test_permissions.py` — 15 test unitari con mock del resolver.
