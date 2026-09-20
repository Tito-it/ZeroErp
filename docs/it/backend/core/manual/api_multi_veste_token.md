# API Login/Refresh Multi-Veste (Core Django, §8.3 PR-B1)

## Scopo

Documenta il contratto HTTP dei 6 endpoint di autenticazione post refactor
multi-face (§8.3.1-§8.3.5): 3 login + 3 refresh, uno per namespace
(admin / portale / shop). Ogni namespace espone solo il subset di vesti
che gli compete; un utente con le credenziali giuste ma senza la veste
corretta riceve un 403 `E_VESTE_NON_ATTIVA` **senza che venga contato
come tentativo di login fallito** (no autoblock).

## Contesto

Post modello 1:N (migration `20260420-01..11`), un singolo `auth_user`
puo' avere piu' identita digitali attive con ruoli applicativi diversi.
Il login deve discriminare quale "veste" sta usando l'utente: il claim
`identita_id` iniettato nel JWT tiene traccia della veste scelta, e
`JwtAuditAuthentication` lo valida a ogni richiesta per popolare le GUC.

## Endpoint

### Login

| Path                          | Vesti ammesse                          | View               |
| ----------------------------- | -------------------------------------- | ------------------ |
| `POST /api/v1/admin/token/`   | `OPERATORE`                            | `AdminTokenView`   |
| `POST /api/v1/portale/token/` | `CLIENTE_PORTALE`, `FORNITORE_PORTALE` | `PortaleTokenView` |
| `POST /api/v1/shop/token/`    | `SHOP_CUSTOMER`                        | `ShopTokenView`    |

### Refresh

| Path                                  | Vesti ammesse                          | View                      |
| ------------------------------------- | -------------------------------------- | ------------------------- |
| `POST /api/v1/admin/token/refresh/`   | `OPERATORE`                            | `AdminTokenRefreshView`   |
| `POST /api/v1/portale/token/refresh/` | `CLIENTE_PORTALE`, `FORNITORE_PORTALE` | `PortaleTokenRefreshView` |
| `POST /api/v1/shop/token/refresh/`    | `SHOP_CUSTOMER`                        | `ShopTokenRefreshView`    |

## Input

### Login (tutti e 3)

```json
{
  "username": "tid",
  "password": "***"
}
```

Headers: nessun auth necessario (endpoint pubblico `AllowAny`).

### Refresh (tutti e 3)

```json
{
  "refresh": "eyJhbGciOi..."
}
```

Headers: nessun auth necessario (il token del body fa fede).

## Output

### Login success (HTTP 200)

```json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi...",
  "password_change_required": false
}
```

`password_change_required` e' presente (valore `true`) solo se
l'identita ha il flag `deve_cambiare_password = true`.

### Refresh success (HTTP 200)

```json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi..."
}
```

Il nuovo refresh e' rotato (`SIMPLE_JWT.ROTATE_REFRESH_TOKENS=True`)
e il vecchio blacklistato (`BLACKLIST_AFTER_ROTATION=True`). I claim
custom (`identita_id`, `ruolo_applicativo`, `sid`) sono **preservati**
nel nuovo refresh (SimpleJWT ruota solo `jti/exp/iat`).

## Claim JWT custom

Oltre ai claim standard SimpleJWT (`token_type`, `exp`, `iat`, `jti`,
`user_id`), il JWT emesso da `MultiVesteTokenSerializer` contiene:

| Claim               | Tipo   | Fonte                                             | Scopo                                                                                                                                                                        |
| ------------------- | ------ | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `identita_id`       | int    | `anagrafiche.identita_digitali.id`                | Discriminatore veste. Usato da `JwtAuditAuthentication` per popolare GUC `app.current_identita_id` + validare che l'identita sia ancora attiva                               |
| `ruolo_applicativo` | string | `anagrafiche.identita_digitali.ruolo_applicativo` | `OPERATORE` \| `CLIENTE_PORTALE` \| `FORNITORE_PORTALE` \| `SHOP_CUSTOMER` \| `API_CLIENT` \| `DISABILITATO`. Letto da guard cross-namespace del refresh + esposto in `/me/` |
| `sid`               | uuid   | `SidTokenObtainPairSerializer.get_token`          | Session ID stabile (invariato tra rotazioni). Usato dall'audit sessioni                                                                                                      |
| `user_id`           | int    | `auth_user.id`                                    | Standard SimpleJWT                                                                                                                                                           |

I claim sono iniettati sul **refresh token**; SimpleJWT li copia
automaticamente sull'access token via property `access_token` (eccezione:
i `no_copy_claims` standard `exp`, `jti`, `token_type`).

Le costanti Python per i claim custom vivono in
`apps/core/services/auth_constants.py`:

```python
JWT_CLAIM_IDENTITA_ID = "identita_id"
JWT_CLAIM_RUOLO_APPLICATIVO = "ruolo_applicativo"
```

**Mai hardcodare i nomi** nei consumer: importare le costanti.

## Guard applicati

### 1. Guard "veste" al login (MultiVesteTokenSerializer, §8.3.2)

Dopo la verifica credenziali (`super().validate()`), il serializer
risolve l'identita attiva dell'utente con `ruolo_applicativo` nel
subset del namespace. Se assente:

- **Esito**: `VesteNonAttivaError` → HTTP 403 `E_VESTE_NON_ATTIVA`
- **No autoblock**: `AuditTokenObtainPairView` intercetta l'eccezione
  prima del catch-all `AuthenticationFailed` e **non** chiama
  `registra_tentativo_login(successo=False)`. Un operatore che
  sbaglia namespace (es. tenta `/portale/token/`) non si autoblocca.

### 2. Guard cross-namespace al refresh (§8.3.5)

Prima di delegare al parent SimpleJWT, `AuditTokenRefreshView.post()`
estrae il claim `ruolo_applicativo` dal refresh token e verifica che
rientri nel set `expected_ruoli_applicativi` del namespace chiamato:

- Refresh OPERATORE su `/portale/token/refresh/` → 403 `E_VESTE_NON_ATTIVA`
- Refresh OPERATORE su `/admin/token/refresh/` → OK

Non c'e' escalation di privilegio (il claim veste viene dal token firmato),
ma chiude l'ambiguita' semantica cross-path.

### 3. Guard identita al request authenticated (§8.3.4)

Ad **ogni** richiesta con Bearer, `JwtAuditAuthentication.authenticate()`:

1. Estrae `identita_id` dal claim. Se assente → 401 `E_JWT_SENZA_IDENTITA`.
2. Query CTE che valida `(auth_user, identita_id)` attivi + popola 6 GUC
   di sessione in singola round-trip. Se count = 0 → 401 `E_IDENTITA_NON_ATTIVA`.
3. Setta marker `request._zeroerp_jwt_guc_set = True` per il reset
   simmetrico via middleware a response.

## Codici errore

| Codice                    | HTTP | UI action         | Quando                                                                         | Policy        |
| ------------------------- | ---- | ----------------- | ------------------------------------------------------------------------------ | ------------- |
| `E_AUTHENTICATION_FAILED` | 401  | show_error_banner | Credenziali errate, token scaduto/invalid                                      | Pre-esistente |
| `E_NOT_AUTHENTICATED`     | 401  | show_error_banner | Header `Authorization` assente su endpoint protetto                            | Pre-esistente |
| `E_VESTE_NON_ATTIVA`      | 403  | show_error_banner | Utente senza identita del namespace chiamato (login) / refresh cross-namespace | §8.3.2        |
| `E_JWT_SENZA_IDENTITA`    | 401  | redirect_login    | JWT senza claim `identita_id` (token pre-refactor)                             | §8.3.4        |
| `E_IDENTITA_NON_ATTIVA`   | 401  | redirect_login    | `identita_id` non corrisponde a identita attiva (revocata)                     | §8.3.4        |
| `E_UTENTE_BLOCCATO`       | 403  | show_error_banner | Identita con `bloccato_fino_a > now()` (tentativi falliti)                     | Pre-esistente |

Tutti i codici sono registrati in `apps/core/services/error_policies.py`.

## Audit sessione

A ogni login/refresh con successo, le view registrano eventi in
`dbops.sessioni_utente`:

- `record_login(user_id, request, jti)` dopo login
- `record_refresh(user_id, request, jti)` dopo refresh

Prima dell'INSERT, le view popolano manualmente le GUC di sessione
tramite `set_jwt_gucs(username, user_id, identita_id, request)`:
senza questo passaggio i trigger di audit scriverebbero
`user_insert = 'zeroerp_app'` invece dell'username effettivo (il login
**non** passa dalla DRF auth chain, quindi `JwtAuditAuthentication`
non e' in gioco).

Se `set_jwt_gucs` ritorna `False` (identita_id assente o identita
revocata), viene loggato `security.{login,refresh}_guc_mancate` e
l'audit procede comunque con GUC vuote.

## Regole

- **Rename breaking (§8.3.1)**: il vecchio path `/api/v1/auth/token/`
  non esiste piu'. I client devono aggiornarsi a `/api/v1/admin/token/`.
  Nessun alias/grace period.
- Le view base `AuditTokenObtainPairView` e `AuditTokenRefreshView` sono
  **astratte**: istanziarle direttamente solleva AssertionError.
  Usare SEMPRE le subclass namespace-specific.
- Il claim `sid` e' preservato da `SidTokenObtainPairSerializer`: il
  `MultiVesteTokenSerializer` eredita da Sid (non da `TokenObtainPairSerializer`
  diretto) — senza questa catena l'audit sessioni si romperebbe.
- Il throttle `LoginRateThrottle` (5 tentativi / 5 minuti per IP) e' applicato
  su **tutte e 3** le view di login (ereditato da `AuditTokenObtainPairView`).

## Dipendenze DB

| Tabella/Funzione                     | Schema        | Ruolo                                                                                                          |
| ------------------------------------ | ------------- | -------------------------------------------------------------------------------------------------------------- |
| `anagrafiche.identita_digitali`      | `anagrafiche` | Bridge auth_user ↔ soggetto_ruolo per veste. `UNIQUE(auth_user_id, ruolo_applicativo)` post migration 20260420 |
| `django.auth_user`                   | `django`      | Credenziali                                                                                                    |
| `dbops.sessioni_utente`              | `dbops`       | Audit login/refresh                                                                                            |
| `script.fn_check_blocco_login`       | `script`      | Blocco tentativi falliti                                                                                       |
| `script.fn_registra_tentativo_login` | `script`      | Incremento/reset contatore                                                                                     |

## File backend

| File                                            | Ruolo                                                                                                                                                                                                                               |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/core/api/auth_views.py`                   | `AuditTokenObtainPairView` (astratta) + 3 subclass login; `AuditTokenRefreshView` (astratta) + 3 subclass refresh; helper `_extract_identita_id_from_refresh`, `_extract_ruolo_applicativo_from_refresh`, `_decode_refresh_payload` |
| `apps/core/api/multi_veste_token_serializer.py` | `MultiVesteTokenSerializer` + 3 subclass (Admin/Portale/Shop), `VesteNonAttivaError`                                                                                                                                                |
| `apps/core/api/jwt_audit_authentication.py`     | `JwtAuditAuthentication` (legge claim + popola GUC), `set_jwt_gucs`, `JwtSenzaIdentitaError`, `IdentitaNonAttivaError`                                                                                                              |
| `apps/core/api/token_serializers.py`            | `SidTokenObtainPairSerializer` (parent di MultiVeste, aggiunge `sid`)                                                                                                                                                               |
| `apps/core/db/auth_repository.py`               | `find_identita_attiva_for_ruoli`, `get_identita_dettaglio`, `check_blocco_login`, `registra_tentativo_login`                                                                                                                        |
| `apps/core/services/auth_constants.py`          | Costanti `JWT_CLAIM_*` + `RUOLO_APPLICATIVO_*`                                                                                                                                                                                      |
| `apps/core/services/error_policies.py`          | Policy `E_VESTE_NON_ATTIVA`, `E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA`                                                                                                                                                        |
| `apps/core/api/error_responses.py`              | `drf_exception_handler` — priorita' a `default_code` E_* delle subclass AuthenticationFailed                                                                                                                                        |
| `backend/zeroerp_backend/urls.py`               | 6 route registrate                                                                                                                                                                                                                  |

## Note di migrazione

- Pre-§8.3: esistevano solo `POST /api/v1/auth/token/` e `/refresh/`, senza
  claim custom nel JWT. Tutti gli utenti con credenziali valide ottenevano
  accesso indistintamente.
- Post-§8.3: il path originale e' stato rimosso (no alias). I 3 namespace
  isolano i canali. I claim custom (`identita_id`, `ruolo_applicativo`)
  permettono a `JwtAuditAuthentication` di distinguere la veste su ogni
  request, sostituendo il vecchio approccio "prima identita attiva"
  ambiguo col modello 1:N.
- Token pre-refactor (senza `identita_id`) vengono rifiutati con
  `E_JWT_SENZA_IDENTITA` (401) — richiesto nuovo login. Grace period 0.

## Documenti correlati

- [Auth Views Audit](auth_views_audit.md) — architettura audit sessioni
- [API User Profile](api_user_profile.md) — `/me/` che espone il blocco `identita`
- [API Invito Operatore](api_invito_operatore.md) — invito + attivazione operatori
- [API Password Reset](api_password_reset.md) — reset password
- [WIP Multi-face Auth](../../../dev/work-done/pr-b-shop-b2c-cambio-modello.md) §8 PR-B1
