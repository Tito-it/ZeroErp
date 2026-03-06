# PermissionResolver (Core Django)

## Scopo

Risolutore centrale dei permessi ZeroErp. Implementa la catena di risoluzione:
`ruolo_sistema → override utente → profilo reparto → BLOCCATO` (default sicuro).

## Contesto

Classe statica in `apps/core/services/permissions_resolver.py`.
Utilizzata da `ZeroERPPermission` (DRF), `EmittenteFiscaleScopeMixin`, `JwtAuditMiddleware`
e dall'endpoint diagnostico `/api/v1/core/users/{id}/permessi-effettivi/`.

Tutti i metodi accettano un dict `cache` opzionale per evitare query duplicate nella stessa
richiesta HTTP. La cache e' un semplice `dict[str, Any]` memorizzato su `request._zeroerp_perms_cache`.

## Costanti

```python
LIVELLO_MAP = {
    "TUTTO":    frozenset({"view", "add", "change", "delete"}),
    "LETTURA":  frozenset({"view"}),
    "BLOCCATO": frozenset(),
}
```

## Metodi pubblici

### `get_ruolo_sistema(user, cache=None) → str | None`

Restituisce il `ruolo_sistema` dell'utente dalla tabella ponte `anagrafiche.risorse_umane_auth_user`.
Ritorna `None` se l'utente non ha un record ponte.

Cache key: `"ruolo_sistema"`.

### `get_livello_area(user, area_schema_db, cache=None) → str`

Restituisce il livello effettivo per un'area funzionale (identificata dal suo `schema_db`).

Catena di risoluzione:
1. `DISABILITATO` → `"BLOCCATO"`
2. `ADMIN` → `"TUTTO"`
3. `UserOverrideArea` (con validita' temporale) → livello override
4. `ProfiloRepartoArea` (ereditato dal reparto) → livello profilo
5. Default → `"BLOCCATO"`

Cache key: `"area:{schema_db}"`.

### `get_livello_oggetto(user, app_label, model_name, area_schema_db, cache=None) → str`

Restituisce il livello effettivo per un singolo model Django.

Catena:
1. `DISABILITATO` → `"BLOCCATO"`, `ADMIN` → `"TUTTO"`
2. `UserOverrideOggetto` (con validita' temporale) → livello override
3. Risale alla catena area (`get_livello_area`)

Cache key: `"oggetto:{app_label}.{model_name}"`.

### `check_azione(user, permission_codename, cache=None) → bool`

Verifica se un'azione di processo e' abilitata per l'utente.

Catena:
1. `DISABILITATO` → `False`, `ADMIN` → `True`
2. `UserOverrideAzione` (con validita' temporale) → `abilitata`
3. `ProfiloRepartoAzione` (ereditato dal reparto) → `abilitata`
4. Default → `False`

Cache key: `"azione:{permission_codename}"`.

### `get_emittenti_ids(user, cache=None) → list[int] | None`

Restituisce gli ID emittenti fiscali autorizzati per l'utente.
`None` = nessuna restrizione (whitelist vuota = vede tutto).

Cache key: `"emittenti_ids"`.

### `get_area_schema_db(app_label, model_name) → str`

Determina lo `schema_db` dell'area per un model Django:
1. Controlla override in `config.area_model_overrides`
2. Altrimenti usa `app_label` (che corrisponde allo schema)

### `has_profilo_reparto_area(user, area_schema_db, cache=None) → bool`

Verifica se il reparto dell'utente ha un profilo configurato per l'area.
Usato da `ZeroERPPermission` per distinguere "BLOCCATO da profilo" da "nessun profilo configurato".

Cache key: `"has_profilo:{schema_db}"`.

## Metodi interni

### `_get_unita_organizzativa_id(user, cache=None) → int | None`

Risale all'unita' organizzativa dell'utente via `risorse_umane_auth_user → risorse_umane`.

Cache key: `"uo_id"`.

### `_resolve_livello_area(user, area_schema_db, cache=None) → str`

Risoluzione area per utenti `OPERATIVO`:
`UserOverrideArea → ProfiloRepartoArea → "BLOCCATO"`.

### `_resolve_livello_oggetto(user, app_label, model_name, area_schema_db, cache=None) → str`

Risoluzione oggetto per utenti `OPERATIVO`:
`UserOverrideOggetto → _resolve_livello_area`.

### `_resolve_azione(user, permission_codename, cache=None) → bool`

Risoluzione azione per utenti `OPERATIVO`:
`UserOverrideAzione → ProfiloRepartoAzione → False`.

## Filtro validita' temporale

Tutti gli override con `valido_dal` / `valido_al` vengono filtrati con:

```python
(Q(valido_dal__isnull=True) | Q(valido_dal__lte=today))
& (Q(valido_al__isnull=True) | Q(valido_al__gte=today))
```

Override scaduti o futuri vengono ignorati silenziosamente, facendo proseguire la catena.

## Dipendenze DB

| Tabella                              | Uso                                  |
|--------------------------------------|--------------------------------------|
| `anagrafiche.risorse_umane_auth_user`| Ruolo sistema e ponte utente-risorsa |
| `anagrafiche.risorse_umane`          | Unita' organizzativa                 |
| `config.user_override_aree`          | Override individuali area            |
| `config.user_override_oggetti`       | Override individuali oggetto         |
| `config.user_override_azioni`        | Override individuali azione          |
| `config.profili_reparto_aree`        | Profili reparto ereditati (area)     |
| `config.profili_reparto_azioni`      | Profili reparto ereditati (azione)   |
| `config.area_model_overrides`        | Riassegnazione model a area diversa  |
| `config.user_emittenti_fiscali`      | Ambito emittente fiscale              |
| `config.aree_funzionali`             | Elenco aree (per endpoint diagnostico)|

## Test

`apps/core/tests/services/test_permissions_resolver.py` — 23 test unitari con mock dei model.
