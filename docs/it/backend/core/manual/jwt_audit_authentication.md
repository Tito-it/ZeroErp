# JwtAuditAuthentication (Core API)

## Scopo

Subclass DRF di `rest_framework_simplejwt.authentication.JWTAuthentication` che propaga
l'identita' utente JWT come GUC PostgreSQL (`app.jwt_user`, `app.current_user_id`) subito
dopo `authenticate()` di successo, prima che il view body inizi a fare INSERT/UPDATE.

E' il punto del flusso DRF in cui:

* l'identita' JWT e' **gia' risolta** (super().authenticate ha verificato il token e caricato
  lo user dal DB)
* il view body **non e' ancora partito** (perform_authentication gira in `initial()`,
  prima del view method)

→ i trigger DB di audit (`script.trgfn_audit_data_user_generic`) e di scope
(`anagrafiche.trgfn_billing_account_link_ef`,
`anagrafiche.trgfn_billing_account_guard_admin_globale`,
`script.trgfn_guard_emittente_scope`) vedono finalmente le GUC durante le scritture.

> **Sostituisce il pattern di setting GUC nel middleware**, che era inerte per le request
> JWT perche' Django middleware `process_view` gira **prima** della DRF authentication.
> Vedi guida [Risorse umane e accessi](/guide/risorse-umane-e-accessi) sezione
> "Propagazione identita utente al database (GUC)" per il razionale completo.

## Contesto

Classe in `apps/core/api/jwt_audit_authentication.py`. Registrata in:

* `settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` (default per ogni view DRF)
* `apps.core.api.base_views.DomainAPIView.authentication_classes` (esplicito)
* `apps.core.api.base_views.AdminAPIView.authentication_classes` (esplicito)
* `apps.ai_assistant.api.views.AIStatusView.authentication_classes` (esplicito)

## Funzionalita'

### `authenticate(request)`

1. Chiama `super().authenticate(request)` (logica JWT invariata: verifica token,
   carica user dal DB)
2. Se `super` ritorna `None` (no token / token invalido) → ritorna `None` invariato,
   nessun side effect
3. Se `super` ritorna `(user, validated_token)`:
   * Estrae `user_id = getattr(user, "id", None)`
   * Se `user_id is None` (caso difensivo, es. mock di test mal configurato) → ritorna
     comunque il risultato senza side effect
   * Altrimenti chiama `_set_gucs(request, user, user_id)` e ritorna `(user, validated_token)`

### `_set_gucs(request, user, user_id)`

Metodo separato (mockabile dai test) che propaga l'identita':

* Apre `connection.cursor()` ed esegue **una sola** query:

  ```sql
  SELECT set_config('app.jwt_user',        %s, false),
         set_config('app.current_user_id', %s, false)
  ```

  Parametri: `[str(user), str(user_id)]`.

* `is_local = false` → **GUC session-scoped**: persiste sulla connessione PG per tutta
  la durata della request, anche fuori dalle `transaction.atomic()` aperte successivamente
  dal view body.

* Se la query fallisce con `DatabaseError` (es. DB down) → log warning, ritorna senza
  sollevare. La request prosegue (i trigger faranno fail-open senza GUC, comportamento
  documentato sui trigger stessi).

* Se la query va a buon fine → setta `request._zeroerp_jwt_guc_set = True`. Questo marker
  viene letto da `JwtAuditMiddleware.process_response` per fare il **reset simmetrico**
  delle GUC a fine request.

## Perche' session-scoped (`set_config(.., false)`) invece di SET LOCAL

A `authenticate()` time la connessione e' in **autocommit Django** (il view body non ha
ancora aperto la sua `transaction.atomic()`). Un `SET LOCAL` o `set_config(.., true)`
verrebbe perso al COMMIT immediato dell'autocommit, e i trigger DB nelle transazioni
successive del service troverebbero le GUC vuote (fail-open silenzioso).

`set_config(.., false)` invece persiste sulla connessione fino al **reset esplicito**
operato da `JwtAuditMiddleware.process_response` o alla **chiusura connessione**
(`CONN_MAX_AGE = 0` di default chiude a fine request, quindi nessun rischio di leak fra
request).

## Sicurezza contro leak fra request

Oggi `CONN_MAX_AGE = 0` (default Django) chiude la connessione al termine di ogni request,
quindi non c'e' rischio di leak.

Per blindare la cosa anche in scenari futuri (`CONN_MAX_AGE > 0`, connection pooling
esterno in transaction-mode), `JwtAuditMiddleware.process_response` resetta esplicitamente
le GUC a stringa vuota, **solo se il marker `_zeroerp_jwt_guc_set` e' settato**.
Questo garantisce simmetria perfetta set/reset e mantiene compatibilita' con i
`SimpleTestCase` API che girano con request anonime a livello middleware.

## Test

`apps/core/tests/api/test_jwt_audit_authentication.py` — 6 test unitari:

| Test | Verifica |
|---|---|
| `test_authenticate_returns_none_passthrough` | Auth fallita (super → None) → no GUC, no flag |
| `test_authenticate_success_sets_gucs` | Auth ok → 1 execute combinata + flag su request |
| `test_set_gucs_uses_session_scope_not_local` | SQL contiene `set_config` + `false`, NO `SET LOCAL` |
| `test_set_gucs_passes_str_user_and_user_id` | Params nell'ordine `[str(user), str(user.id)]` |
| `test_set_gucs_database_error_swallowed` | DB down → log warning, ritorna senza raise, flag NON settato |
| `test_user_without_id_skipped` | User senza `.id` (caso difensivo) → no GUC |

I test API che usano `Django test client` + `SimpleTestCase` mockano `_set_gucs` via la
base class [`JwtMockedApiTest`](../../../../backend/apps/core/tests/_helpers/jwt_mock.py)
(in `apps/core/tests/_helpers/jwt_mock.py`) per evitare `cursor.execute` durante l'auth
in test (vietato in `SimpleTestCase` da `DatabaseOperationForbidden`).

## Pattern complementare per entry point non-HTTP

`JwtAuditAuthentication` copre **automaticamente** tutte le request HTTP JWT, ma per
definizione non vede:

* `manage.py` command (import batch, migrazione dati)
* Cron job / task pgAgent
* Worker background / signal handlers
* Test di integrazione che chiamano i service direttamente

Per questi casi futuri il pattern raccomandato e' un helper `app_atomic(auth_user_id=...)`
a livello service, **da implementare quando servira'** (oggi non esistono entry point
non-HTTP che scrivono entita' audited). Vedi guida
[Risorse umane e accessi](/guide/risorse-umane-e-accessi) sezione
"Pattern complementare per entry point non-HTTP (futuro)".

## Riferimenti

* [JwtAuditMiddleware](jwt_audit_middleware.md) — middleware compagno (cache + DISABILITATO + reset GUC)
* [Risorse umane e accessi — Propagazione identita utente al database (GUC)](/guide/risorse-umane-e-accessi)
* [Parametri Personalizzati GUC](/postgresql/parametri-personalizzati-(GUC)) — semantica session-scoped vs transaction-scoped
* [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
