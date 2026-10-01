# JwtAuditAuthentication (Core API)

## Scopo

Subclass DRF di `rest_framework_simplejwt.authentication.JWTAuthentication` che, subito
dopo un `authenticate()` di successo e prima che il view body inizi a scrivere:

* verifica i claim obbligatori del JWT interno (`identita_id`, `sid`);
* valida che l'identita del claim sia ancora attiva per quell'`auth_user`;
* propaga utente, veste ed emittente attivo come **6 GUC PostgreSQL** session-scoped.

E' il punto del flusso DRF in cui:

* l'identita' JWT e' **gia' risolta** (super().authenticate ha verificato il token e caricato
  lo user dal DB)
* il view body **non e' ancora partito** (perform_authentication gira in `initial()`,
  prima del view method)

→ i trigger DB di audit (`script.trgfn_audit_data_user_generic`), di scope
(`anagrafiche.trgfn_billing_account_link_ef`,
`anagrafiche.trgfn_billing_account_guard_admin_globale`,
`script.trgfn_guard_emittente_scope`) e le funzioni di permesso/RLS vedono le GUC
durante le scritture.

> Il setting delle GUC non avviene nel middleware: Django `process_view` gira **prima**
> della DRF authentication, quando `request.user` e' ancora anonimo per le request JWT.
> Il middleware compagno [`JwtAuditMiddleware`](jwt_audit_middleware.md) si occupa del
> reset di inizio richiesta. Vedi guida [Risorse umane e accessi](/guide/risorse-umane-e-accessi)
> sezione "Propagazione identita utente al database (GUC `app.*`)".

## Contesto

File `apps/core/api/jwt_audit_authentication.py`. Contiene:

* `JWT_IDENTITY_GUCS` — la tupla dei 6 GUC d'identita, unica fonte di verita'
* `JWT_GUC_RESET_SQL` — SQL di azzeramento derivato dalla tupla (usato dal middleware)
* `set_jwt_gucs(...)` — helper che valida l'identita e popola i GUC
* `JwtAuditAuthentication` — la classe di autenticazione
* le eccezioni `JwtSenzaIdentitaError`, `JwtSenzaSidError`, `IdentitaNonAttivaError`

La classe e' registrata in:

* `settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` (default per ogni view DRF)
* `authentication_classes` esplicito di `DomainAPIView`, `AdminAPIView`, `PortaleAPIView`,
  `ShopAPIView` (`apps/core/api/base_views.py`)
* `apps.ai_assistant.api.views.AIStatusView.authentication_classes` (esplicito)

## I 6 GUC

| GUC | Valore |
| --- | --- |
| `app.jwt_user` | username Django |
| `app.current_user_id` | `auth_user.id` |
| `app.current_identita_id` | `identita_digitali.id` (vuoto se l'identita non e' attiva) |
| `app.ruolo_applicativo` | `ruolo_applicativo` dell'identita |
| `app.soggetto_ruolo_id` | `soggetto_ruolo_id` dell'identita |
| `app.current_emittente_id` | emittente attivo del claim, se ancora attivo (altrimenti vuoto) |

Il contratto completo dei GUC e' nella guida [Contratto GUC `app.*`](/guide/contratto-guc-app).

## Funzionalita'

### `set_jwt_gucs(*, username, user_id, identita_id=None, emittente_attivo_id=None, request=None) -> bool`

Helper riusato da `JwtAuditAuthentication` e dalle view di login/refresh
([auth_views_audit.md](auth_views_audit.md)), che non passano dalla catena di
autenticazione DRF.

* Se `identita_id` e' `None` → ritorna `False` senza query: nel modello 1:N un
  `auth_user` puo' avere piu' identita attive e non se ne risolve una implicita.
* Altrimenti esegue **una sola** query CTE che:
  * cerca l'identita `id = identita_id AND auth_user_id = user_id AND attivo = true`;
  * cerca l'emittente del claim tra gli `emittenti_fiscali` attivi;
  * imposta i 6 GUC con `set_config(..., false)`: `app.jwt_user` e
    `app.current_user_id` sempre, i 3 GUC d'identita tutti insieme o tutti vuoti,
    `app.current_emittente_id` vuoto se il claim manca o l'emittente non e' attivo;
  * ritorna il numero di identita trovate.
* Ritorna `True` se l'identita e' attiva, `False` altrimenti.
* `DatabaseError` → log warning `jwt_audit_authentication.set_gucs_failed`, ritorna `False`.
* Se l'identita e' trovata e `request` e' fornito, imposta
  `request._zeroerp_jwt_guc_set = True`.

Lo scope emittente non si rivalida qui: se ne occupa il DB a ogni chiamata.

### `authenticate(request)`

1. Chiama `super().authenticate(request)` (verifica token, carica user dal DB).
2. `super` ritorna `None` (nessun token) → ritorna `None`, nessun side effect.
3. `user` senza `.id` o `validated_token` `None` (casi difensivi dei test) → ritorna
   il risultato senza side effect.
4. Claim `identita_id` assente → `JwtSenzaIdentitaError` (401 `E_JWT_SENZA_IDENTITA`).
5. Claim `sid` assente o vuoto → `JwtSenzaSidError` (401 `E_JWT_SENZA_SID`).
6. Chiama `_set_gucs(request, user, user_id, int(identita_id), emittente_attivo_id=...)`;
   il claim `emittente_attivo_id` e' opzionale (assente = «Tutti gli emittenti»).
7. `_set_gucs` ritorna `False` → `IdentitaNonAttivaError` (401 `E_IDENTITA_NON_ATTIVA`).
8. Ritorna `(user, validated_token)`.

`_set_gucs(request, user, user_id, identita_id, *, emittente_attivo_id=None) -> bool` e'
un metodo separato, mockabile dai test, che delega a `set_jwt_gucs`.

### Codici errore

| Eccezione | Codice | HTTP | Quando |
| --- | --- | --- | --- |
| `JwtSenzaIdentitaError` | `E_JWT_SENZA_IDENTITA` | 401 | claim `identita_id` mancante |
| `JwtSenzaSidError` | `E_JWT_SENZA_SID` | 401 | claim `sid` mancante o vuoto |
| `IdentitaNonAttivaError` | `E_IDENTITA_NON_ATTIVA` | 401 | identita non attiva / non dell'utente, **oppure** query GUC fallita |

Classe `NON_AUTENTICATO` in `error_policies_generated.py` (`CLASSE_PER_CODICE`). Con il
DB non raggiungibile durante la query GUC la request non prosegue: esce 401
`E_IDENTITA_NON_ATTIVA`.

## Perche' session-scoped (`set_config(.., false)`) invece di SET LOCAL

A `authenticate()` time la connessione e' in **autocommit Django** (il view body non ha
ancora aperto la sua `transaction.atomic()`). Un `SET LOCAL` o `set_config(.., true)`
verrebbe perso al COMMIT immediato dell'autocommit, e i trigger DB nelle transazioni
successive del service troverebbero le GUC vuote.

`set_config(.., false)` invece persiste sulla connessione.

## Sicurezza contro leak fra request

Il progetto usa connessioni persistenti (`CONN_MAX_AGE`, default `600` in `settings.py`):
una connessione serve piu' request in sequenza. Il leak dei GUC fra request e' chiuso
da `JwtAuditMiddleware.process_request`, che azzera tutti i `JWT_IDENTITY_GUCS` (via
`JWT_GUC_RESET_SQL`) **all'inizio** di ogni richiesta `/api/`, prima di questa auth class.
Dettagli in [jwt_audit_middleware.md](jwt_audit_middleware.md).

## Test

`apps/core/tests/api/test_jwt_audit_authentication.py` — unitari con `connection`
mockata: passthrough senza token, popolamento GUC in una sola execute session-scoped,
parametri della CTE, claim emittente propagato o assente, DB giu' → 401
`E_IDENTITA_NON_ATTIVA`, i tre 401 sui claim e sull'identita.

I test API che usano `Django test client` + `SimpleTestCase` mockano `_set_gucs` via la
base class [`JwtMockedApiTest`](../../../../../backend/apps/core/tests/_helpers/jwt_mock.py)
(in `apps/core/tests/_helpers/jwt_mock.py`) per evitare `cursor.execute` durante l'auth
in test (vietato in `SimpleTestCase` da `DatabaseOperationForbidden`).

## Entry point non-HTTP

`JwtAuditAuthentication` copre **automaticamente** tutte le request HTTP JWT, ma per
definizione non vede management command, job schedulati, worker di background e test
di integrazione che chiamano i service direttamente. Vedi guida
[Risorse umane e accessi](/guide/risorse-umane-e-accessi) sezione
"Per gli entry point non-HTTP".

## Riferimenti

* [JwtAuditMiddleware](jwt_audit_middleware.md) — middleware compagno (reset GUC, guard BYPASSRLS)
* [Auth Views Audit](auth_views_audit.md) — login/refresh che chiamano `set_jwt_gucs` direttamente
* [Risorse umane e accessi — Propagazione identita utente al database (GUC)](/guide/risorse-umane-e-accessi)
* [Contratto GUC `app.*`](/guide/contratto-guc-app)
* [Parametri Personalizzati GUC](/postgresql/parametri-personalizzati-(GUC)) — semantica session-scoped vs transaction-scoped
* [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
