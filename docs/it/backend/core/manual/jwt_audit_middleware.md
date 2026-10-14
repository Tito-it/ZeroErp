# JwtAuditMiddleware (Core Django)

## Scopo

Middleware Django per le request `/api/*`. Responsabilita':

1. **Reset dei GUC d'identita all'inizio della richiesta** (`process_request`): azzera i 6
   `JWT_IDENTITY_GUCS` prima dell'autenticazione DRF e di ogni query della view.
2. **Guard BYPASSRLS** (`process_request`): rifiuta le richieste se la connessione web
   gira su un ruolo PostgreSQL che bypassa la RLS.

> ⛔ **Il rifiuto dei `DISABILITATO` non sta qui** (ritirato il 2026-09-28, S-2 dell'
> [analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).
> Stava in `process_view`, dove `request.user` e' l'utente di **sessione** di Django: per un
> client Bearer JWT e' ancora `AnonymousUser` (l'autenticazione DRF gira dopo, nel dispatch
> della view), quindi il ramo non scattava mai. Dal 2026-10-02 `DISABILITATO` non è più un
> ruolo (brief area Accessi, R-DB-1): una veste spenta tiene il suo tipo con `attivo = false`,
> la tabella rifiuta `DISABILITATO`, e chi ha solo vesti spente non ha un'identità attiva —
> lo nega la catena di [ZeroERPPermission](zeroerp_permission.md) al livello d'area.

> ⛔ **La cache permessi L2 non si precarica qui** (fino al 2026-09-24 si'). La sua chiave
> e' il contesto di sessione (identita' + emittente effettivo), che nasce in
> `set_jwt_gucs` durante l'autenticazione DRF, cioe' **dopo** questo middleware. La
> carica una sede sola, `ZeroERPPermission._get_cache()`: vedi
> [permissions_cache.md](permissions_cache.md).

> **La propagazione delle GUC non avviene qui.** Il setting e' fatto da
> [`JwtAuditAuthentication`](jwt_audit_authentication.md), registrata in
> `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`, dopo il reset di questo middleware.
> Vedi guida [Risorse umane e accessi](/guide/risorse-umane-e-accessi) sezione
> "Propagazione identita utente al database (GUC `app.*`)".

## Contesto

Classe in `apps/core/middleware/jwt_audit_middleware.py`.
Registrata in `settings.MIDDLEWARE` dopo `AuthenticationMiddleware`.

## Funzionalita'

### 1. Reset GUC di inizio richiesta (`process_request`)

Per ogni richiesta su path `/api/`, **anche anonima**:

- se `connection.connection is None` (nessuna connessione ancora aperta) → nessuna
  operazione: una sessione PostgreSQL nuova ha i GUC gia' vuoti;
- altrimenti esegue `JWT_GUC_RESET_SQL` (derivato da `JWT_IDENTITY_GUCS` in
  `apps/core/api/jwt_audit_authentication.py`): una sola query che porta a stringa
  vuota tutti e 6 i GUC d'identita (`app.jwt_user`, `app.current_user_id`,
  `app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id`,
  `app.current_emittente_id`).

Il reset e' incondizionato (non dipende da marker dell'auth) e **fail-closed**: se la
query solleva `DatabaseError` il middleware logga
`jwt_audit_middleware.guc_reset_at_start_failed` e risponde **500
`E_GUC_RESET_FAILED`** senza servire la richiesta.

**Perche' all'inizio**: il progetto usa connessioni persistenti (`CONN_MAX_AGE`, default
`600` in `settings.py`) e i GUC sono session-scoped (`set_config(..., false)`). Un reset
di fine richiesta potrebbe non girare (eccezione, crash); quello di inizio garantisce
che ogni richiesta parta da GUC vuoti qualunque sia stato l'esito della precedente
sulla stessa connessione. Dopo il reset, `JwtAuditAuthentication` ripopola i valori per
gli autenticati; gli anonimi restano con GUC vuoti.

### 2. Guard BYPASSRLS (`process_request`)

Dopo il reset, se la connessione esiste, verifica **una volta per processo** (flag di
modulo `_WEB_CONN_ROLE_VERIFIED`) con `connection_role_bypasses_rls()` che il ruolo della
connessione web non bypassi la RLS:

- ruolo con BYPASSRLS → log critical `security.web_connection_is_bypassrls`, **500
  `E_DB_ROLE_UNSAFE`**;
- verifica fallita per `DatabaseError` → log, **500 `E_DB_ROLE_UNSAFE`**;
- verifica superata → il flag passa a `True` e il controllo non si ripete nel processo.

> `E_GUC_RESET_FAILED` ed `E_DB_ROLE_UNSAFE` sono a catalogo come `TECNICO` dal
> 2026-10-07 (classe, frase di ripiego, causa e soluzione per chi gestisce la
> macchina): prima mancavano, e chi leggeva `dbops.error_log` trovava un codice
> che il catalogo non conosceva (E-1 dell'[analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).
> La risposta resta costruita qui (`_json_error`, 500), non dal traduttore.

### 3. Path non API

Per i path che non iniziano con `/api/` il middleware non esegue alcuna operazione.

## Formato risposte d'errore

Le risposte del middleware non passano dal DRF exception handler: le costruisce
`_json_error()` con l'envelope standard.

```json
{
  "error": {
    "code": "E_GUC_RESET_FAILED",
    "message": "Errore interno di sicurezza sessione."
  },
  "meta": {
    "request_id": "<uuid>"
  }
}
```

`meta` contiene `request_id` e `idempotency_key` solo se presenti; se mancano entrambi
`meta` e' omesso.

| Codice | HTTP | Messaggio | Quando |
| --- | --- | --- | --- |
| `E_GUC_RESET_FAILED` | 500 | Errore interno di sicurezza sessione. | reset GUC di inizio richiesta fallito |
| `E_DB_ROLE_UNSAFE` | 500 | Errore interno di sicurezza sessione. | connessione su ruolo BYPASSRLS o verifica fallita |

## Security logging

```text
security.web_connection_is_bypassrls path=<path> ...          (critical)
jwt_audit_middleware.guc_reset_at_start_failed path=<path>    (exception)
jwt_audit_middleware.bypassrls_check_failed path=<path>       (exception)
```

## Flusso

```text
process_request(request)
  │
  ├── path non /api/*                → None (prosegui)
  ├── connessione non ancora aperta  → None (GUC gia' puliti)
  ├── JWT_GUC_RESET_SQL (6 GUC)      → DatabaseError? → 500 E_GUC_RESET_FAILED
  └── guard BYPASSRLS (1 volta/processo)
        └── bypass o errore?         → 500 E_DB_ROLE_UNSAFE
```

## Dipendenze

- `apps.core.api.jwt_audit_authentication.JWT_GUC_RESET_SQL` — SQL di reset derivato da `JWT_IDENTITY_GUCS`
- `apps.core.services.system_context.connection_role_bypasses_rls()` — verifica del ruolo della connessione
- `apps.core.services.request_context` — `get_request_id()`, `get_idempotency_key()` per `meta`

## Note

- Un controllo che non scatta non e' difesa in profondita': e' una seconda sede che
  sembra proteggere. Per questo il rifiuto `DISABILITATO` e' stato tolto invece di
  lasciarlo accanto a `ZeroERPPermission`; il presidio
  `test_il_middleware_non_ha_process_view` impedisce che torni.
- **Storico audit pre-fix**: i record creati prima dello sprint BE-2.0bis
  hanno `user_insert`/`user_update` popolati con il ruolo DB (`zeroerp_app`/`titodb`)
  anziche' lo username JWT, perche' la GUC `app.jwt_user` non veniva propagata correttamente.
  Lo storico non viene riscritto.

## Test

`apps/core/tests/middleware/test_jwt_audit_middleware.py` — test unitari.
