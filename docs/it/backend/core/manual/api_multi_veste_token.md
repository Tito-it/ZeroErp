# API Login/Refresh Multi-Veste (Core Django, §8.3 PR-B1)

## Scopo

Documenta il contratto HTTP degli endpoint di autenticazione post refactor
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

⭐ **Quando una veste «vale» lo decide il DB** (dal 2026-10-07,
brief-db-veste-utilizzabile): `script.fn_veste_utilizzabile(identita_id)` —
accesa, oggi nelle sue date (estremi compresi), soggetto attivo e, per
l'operatore umano, rapporto di lavoro attivo e nelle sue date. Login, ogni
richiesta, refresh, secondo passo del secondo fattore e cambio password
chiedono a lui, e nessun punto del backend guarda `attivo` o le date da solo.
Spenta e fuori date hanno lo **stesso esito** (D-4): nessun codice per le date.

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

### Login

La **chiave d'ingresso** è della porta (dal 2026-10-06, L-4 del piano accessi, D-9):

| Porta | Corpo | Ricerca della credenziale |
| --- | --- | --- |
| `admin` | `{"username": "tid", "password": "***"}` | nome utente esatto (`ModelBackend`) |
| `portale`, `shop` | `{"email": "ada@example.it", "password": "***"}` | email senza maiuscole: `script.fn_get_auth_user_id_for_email`, via `CredenzialePerEmailBackend` |

* Il campo si normalizza nel serializer (spazi ai bordi; l'email anche in
  minuscolo), e **lo stesso valore** va al lookup, ad `authenticate` e
  all'impronta del nome tentato del freno (R-7): con un'email inesistente,
  `Ada@x.it` e `ada@x.it` sono lo stesso nome frenato.
* Il campo dell'altra porta non è il contratto: `{"username": …}` sul portale
  è un **400** (campo `email` obbligatorio), non un tentativo.
* La password arriva com'è digitata, su ogni porta (S-5).
* Sede: `_IngressoPerEmailSerializer` (`username_field = "email"`,
  `trova_credenziale`) in `multi_veste_token_serializer.py`; BB
  `apps/core/services/credenziale_ingresso.py`; `AUTHENTICATION_BACKENDS` in
  `settings.py` (il backend dell'email non si lega a una chiamata con `username`).

Headers: nessun auth necessario (endpoint pubblico `AllowAny`).

### Refresh (tutti e 3)

Corpo **vuoto**: il refresh token arriva dal cookie `zeroerp_refresh`, che il
browser manda da solo (vedi [Cookie di refresh](#cookie-di-refresh)).

```http
POST /api/v1/admin/token/refresh/
X-Requested-With: XMLHttpRequest
Cookie: zeroerp_refresh=eyJhbGciOi...
```

Headers:

- nessun `Authorization`: la sessione la porta il solo cookie;
- `X-Requested-With: XMLHttpRequest` **obbligatorio** (anti-CSRF): e' l'unico
  endpoint autenticato dal solo cookie, e un form o un link di un altro sito
  non puo' mandare un header custom. Senza l'header → 403 `E_PERMISSION_DENIED`,
  prima ancora di leggere il cookie.

Senza cookie (o con cookie vuoto) → 401 `E_AUTHENTICATION_FAILED`
(`InvalidToken`): il client torna al login.

## Output

### Login success (HTTP 200)

```http
HTTP/1.1 200 OK
Set-Cookie: zeroerp_refresh=eyJhbGciOi...; HttpOnly; Max-Age=86400; Path=/api/v1/; SameSite=Strict; Secure
```

```json
{
  "access": "eyJhbGciOi...",
  "password_change_required": true
}
```

Il corpo porta solo l'`access`: il refresh esce nel `Set-Cookie`, mai nel
corpo. La view lo sposta come ultimo passo (`sposta_refresh_nel_cookie`),
dopo l'audit e le GUC che ne leggono ancora i claim.

`password_change_required` e' presente (valore `true`) solo se la
**credenziale** ha l'obbligo di cambio password (`fn_get_deve_cambiare_password`:
e' della credenziale, non della veste — vale su ogni porta); altrimenti la
chiave **manca** (non vale mai `false`).

### Login col secondo fattore attivo (HTTP 200, nessun token)

Se la credenziale ha il secondo fattore **attivo** (`script.fn_get_totp_device`
→ `ATTIVO`), la password giusta **non** apre la sessione: niente `access`, niente
cookie, niente successo sul freno della credenziale né riga `LOGIN`.

```json
{
  "two_factor_required": true,
  "sfida": "eJyrVkrLz1eyUlA...",
  "scade_in_secondi": 300
}
```

La sfida è firmata (`apps/core/services/sfida_secondo_fattore.py`), vale 5 minuti e
porta credenziale, veste, porta e provenienza. ⚠️ SimpleJWT emette comunque access e
refresh, che non escono dalla view (una riga in più fra gli `OutstandingToken`).

### Secondo passo del login (secondo fattore)

| Path | View |
| --- | --- |
| `POST /api/v1/admin/token/secondo-fattore/` | `AdminSecondoFattoreTokenView` |
| `POST /api/v1/portale/token/secondo-fattore/` | `PortaleSecondoFattoreTokenView` |
| `POST /api/v1/shop/token/secondo-fattore/` | `ShopSecondoFattoreTokenView` |

Corpo: `{"sfida", "codice"}` (l'app di autenticazione) oppure `{"sfida",
"codice_recupero"}`. Risposta nell'envelope:

```json
{ "data": { "access": "eyJ...", "password_change_required": true, "codici_recupero_rimasti": 7 } }
```

col refresh nel `Set-Cookie` (solo su 200). `codici_recupero_rimasti` c'è solo se
si è entrati con un codice di recupero. Rifiuti:

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_TOTP_SFIDA_NON_VALIDA` | 401 | sfida scaduta, manomessa, di un'altra porta o provenienza; veste, device o credenziale cambiati fra i due passi. Si riparte dalla password |
| `E_TOTP_CODICE_NON_VALIDO` | 400 | codice sbagliato — conta come una password sbagliata |
| `E_TOTP_PASSO_GIA_USATO` | 400 | codice già usato — conta come una password sbagliata |
| `E_TOTP_RECOVERY_NON_VALIDO` | 400 | codice di recupero sbagliato o già usato — conta |
| `E_CREDENZIALE_BLOCCATA` / `E_UTENTE_BLOCCATO` / `E_LOGIN_ATTESA` | 403 | il freno, ricontrollato prima del codice |

Il successo sul freno si registra **solo** qui (`chiudi_accesso_riuscito`, la sede
comune ai due passi): la password giusta non azzera i tentativi del codice. La riga
`LOGIN` porta `dettaglio.secondo_fattore` (`TOTP` / `CODICE_RECUPERO`). Throttle
proprio, `SecondoFattoreRateThrottle` ([api_throttling.md](api_throttling.md)).
Configurazione del secondo fattore: [api_secondo_fattore.md](api_secondo_fattore.md).

### Refresh success (HTTP 200)

```http
HTTP/1.1 200 OK
Set-Cookie: zeroerp_refresh=eyJhbGciOi...; HttpOnly; Max-Age=86400; Path=/api/v1/; SameSite=Strict; Secure
```

```json
{
  "access": "eyJhbGciOi..."
}
```

Il nuovo refresh e' rotato (`SIMPLE_JWT.ROTATE_REFRESH_TOKENS=True`), il
vecchio blacklistato (`BLACKLIST_AFTER_ROTATION=True`), e torna nel
`Set-Cookie` al posto del precedente. I claim custom (`identita_id`,
`ruolo_applicativo`, `sid`, `emittente_attivo_id`) sono **preservati** nel
nuovo refresh (SimpleJWT ruota solo `jti/exp/iat`). La validazione (firma,
scadenza, blacklist, rotazione) e' quella di `TokenViewBase.post`, col refresh
preso dal cookie (`AuditTokenRefreshView._rinnova`).

### Cookie di refresh

Dal 2026-09-28 il refresh token non viaggia mai nel corpo, ne' in entrata ne'
in uscita: sta in un cookie che lo script della pagina non puo' leggere. La
sede unica di nome, attributi, lettura, scrittura e cancellazione e' il
building block `apps/core/api/refresh_cookie.py`.

| Attributo  | Valore                                                                                          |
| ---------- | ----------------------------------------------------------------------------------------------- |
| Nome       | `zeroerp_refresh`                                                                               |
| `HttpOnly` | sempre                                                                                          |
| `SameSite` | `Strict`                                                                                        |
| `Path`     | `/api/v1/` — il refresh serve anche a logout, cambio password e cambio emittente attivo, che stanno fuori da `/token/` |
| `Secure`   | setting `REFRESH_COOKIE_SECURE` (segue `SESSION_COOKIE_SECURE`: attivo fuori da `DEBUG`)       |
| `Max-Age`  | `SIMPLE_JWT.REFRESH_TOKEN_LIFETIME` (1 giorno): il cookie non sopravvive al token che porta    |

Lo scrivono login e refresh dei tre canali, il cambio password e il cambio
emittente attivo; lo legge il logout, che lo cancella
([api_logout.md](api_logout.md)).

L'access token resta nel corpo, dura `SIMPLE_JWT.ACCESS_TOKEN_LIFETIME` =
**10 minuti**, e il frontend lo tiene solo in memoria, rinnovandolo in silenzio
dal cookie.

## Claim JWT custom

Oltre ai claim standard SimpleJWT (`token_type`, `exp`, `iat`, `jti`,
`user_id`), il JWT emesso da `MultiVesteTokenSerializer` contiene i claim seguenti.
Li inietta `emetti_refresh_veste(user, identita)`, la catena **unica** di chi apre una
sessione: il login e — dal 2026-09-24 — il cambio password
([api_token_cambio_password.md](api_token_cambio_password.md)).

| Claim               | Tipo   | Fonte                                             | Scopo                                                                                                                                                                        |
| ------------------- | ------ | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `identita_id`       | int    | `anagrafiche.identita_digitali.id`                | Discriminatore veste. Usato da `JwtAuditAuthentication` per popolare GUC `app.current_identita_id` + validare che l'identita sia ancora attiva                               |
| `ruolo_applicativo` | string | `anagrafiche.identita_digitali.ruolo_applicativo` | `OPERATORE` \| `CLIENTE_PORTALE` \| `FORNITORE_PORTALE` \| `SHOP_CUSTOMER` \| `API_CLIENT` (`DISABILITATO` non e' piu' un tipo di veste dal 2026-10-02, R-DB-1). Letto da guard cross-namespace del refresh + esposto in `/me/` |
| `sid`               | uuid   | `SidTokenObtainPairSerializer.get_token`          | Session ID stabile (invariato tra rotazioni). Usato dall'audit sessioni                                                                                                      |
| `emittente_attivo_id` | int  | `EmittenteAttivoService.risolvi_per_login`        | **Opzionale, solo veste `OPERATORE`**: emittente attivo (impersonazione di scope). Claim assente = «Tutti gli emittenti». Popola la GUC `app.current_emittente_id`, rivalidata (emittente ancora attivo) a ogni richiesta |
| `user_id`           | int    | `auth_user.id`                                    | Standard SimpleJWT                                                                                                                                                           |

I claim sono iniettati sul **refresh token**; SimpleJWT li copia
automaticamente sull'access token via property `access_token` (eccezione:
i `no_copy_claims` standard `exp`, `jti`, `token_type`).

Le costanti Python per i claim custom vivono in
`apps/core/services/auth_constants.py`:

```python
JWT_CLAIM_IDENTITA_ID = "identita_id"
JWT_CLAIM_RUOLO_APPLICATIVO = "ruolo_applicativo"
JWT_CLAIM_SID = "sid"
JWT_CLAIM_EMITTENTE_ATTIVO_ID = "emittente_attivo_id"
```

**Mai hardcodare i nomi** nei consumer: importare le costanti.

## Guard applicati

### 1. Guard "veste" al login (MultiVesteTokenSerializer, §8.3.2)

Dopo la verifica credenziali (`super().validate()`), il serializer
risolve la prima veste **utilizzabile** dell'utente con `ruolo_applicativo`
nel subset del namespace (`AuthRepository.find_veste_utilizzabile_per_ruoli`):
con una veste scaduta e un'altra valida della stessa porta entra la valida.
Se nessuna:

- **Esito**: `VesteNonAttivaError` → HTTP 403 `E_VESTE_NON_ATTIVA`
- **No autoblock**: `AuditTokenObtainPairView` intercetta l'eccezione
  prima del catch-all `AuthenticationFailed` e **non** chiama
  `registra_tentativo_login(successo=False)`. Un operatore che
  sbaglia namespace (es. tenta `/portale/token/`) non si autoblocca.

### 2. Guard cross-namespace al refresh (§8.3.5)

Prima della validazione SimpleJWT (`_rinnova`), `AuditTokenRefreshView.post()`
controlla l'header anti-CSRF, legge il refresh dal cookie, ne
estrae il claim `ruolo_applicativo` e verifica che
rientri nel set `expected_ruoli_applicativi` del namespace chiamato:

- Refresh OPERATORE su `/portale/token/refresh/` → 403 `E_VESTE_NON_ATTIVA`
- Refresh OPERATORE su `/admin/token/refresh/` → OK
- Refresh nostro senza claim `ruolo_applicativo` → 403 `E_VESTE_NON_ATTIVA`
  (il guard gira **prima** della validazione SimpleJWT, che ruoterebbe il token).
- Refresh illeggibile o con una firma non nostra → 401 `E_AUTHENTICATION_FAILED`:
  la veste si legge solo da claim con la **firma verificata** (BB
  `claims_refresh_firmati`, lo stesso del logout; E-8, chiuso 2026-09-28).

Non c'e' escalation di privilegio (il claim veste viene dal token firmato),
ma chiude l'ambiguita' semantica cross-path.

### 2-bis. Veste non utilizzabile al refresh (D-5, 2026-10-02; date dal 2026-10-07)

Subito dopo il guard cross-namespace, e **prima** della rotazione,
`AuditTokenRefreshView.post()` controlla che la veste del claim `identita_id`
sia ancora utilizzabile sulla credenziale del token (`_veste_utilizzabile` →
`AuthRepository.get_veste_utilizzabile`: id della veste + `user_id` +
`script.fn_veste_utilizzabile`, lo stesso building block di `set_jwt_gucs`):

- Veste utilizzabile → si prosegue col rinnovo.
- Veste spenta, fuori dalle sue date (o, per l'operatore, col rapporto chiuso),
  inesistente o di un'altra credenziale, oppure claim
  `identita_id` assente → 401 `E_AUTHENTICATION_FAILED`, nessuna rotazione, e
  la sessione del token presentato (per `sid`) finisce in blacklist: una veste
  riaccesa dopo **non** la resuscita, si rientra col login.
- Guasto nella lettura della veste → l'errore propaga (500): il refresh non si
  concede su un dubbio.

La regola vale per **qualunque** strada spenga la veste (interruttore
«Accesso attivo», «Disabilita», portale, shop) e per una data che passa. Fino al 2026-10-02 il controllo
stava solo in `set_jwt_gucs`, dopo la rotazione, e un esito negativo era un
warning: la richiesta veniva rifiutata (401 `E_IDENTITA_NON_ATTIVA`, §3), ma il
refresh ruotava ancora.

### 3. Guard identita al request authenticated (§8.3.4)

Ad **ogni** richiesta con Bearer, `JwtAuditAuthentication.authenticate()`:

1. Estrae `identita_id` dal claim. Se assente → 401 `E_JWT_SENZA_IDENTITA`.
   Poi verifica il claim `sid`: se assente o vuoto → 401 `E_JWT_SENZA_SID`.
2. Query CTE che valida `(auth_user, identita_id)` con
   `script.fn_veste_utilizzabile` + popola 6 GUC di sessione in singola
   round-trip. Se count = 0 → 401 `E_IDENTITA_NON_ATTIVA`: una veste che
   scade a sessione aperta chiude la sessione alla richiesta successiva.
3. Setta marker `request._zeroerp_jwt_guc_set = True` per il reset
   simmetrico via middleware a response.

## Codici errore

| Codice                    | HTTP | UI action         | Quando                                                                         | Policy        |
| ------------------------- | ---- | ----------------- | ------------------------------------------------------------------------------ | ------------- |
| `E_AUTHENTICATION_FAILED` | 401  | show_error_banner | Credenziali errate; refresh senza cookie `zeroerp_refresh` o con refresh non valido/scaduto/in blacklist; refresh di una veste non utilizzabile (§2-bis) | Pre-esistente |
| `E_NOT_AUTHENTICATED`     | 401  | show_error_banner | Header `Authorization` assente su endpoint protetto                            | Pre-esistente |
| `E_PERMISSION_DENIED`     | 403  | show_error_banner | Refresh senza header `X-Requested-With: XMLHttpRequest` (anti-CSRF)            | 2026-09-28    |
| `E_VESTE_NON_ATTIVA`      | 403  | show_error_banner | Utente senza una veste utilizzabile (accesa e nelle sue date) del namespace chiamato (login) / refresh cross-namespace | §8.3.2        |
| `E_JWT_SENZA_IDENTITA`    | 401  | redirect_login    | JWT senza claim `identita_id` (token pre-refactor)                             | §8.3.4        |
| `E_JWT_SENZA_SID`         | 401  | redirect_login    | JWT senza claim `sid` (o con `sid` vuoto)                                      | —             |
| `E_IDENTITA_NON_ATTIVA`   | 401  | redirect_login    | `identita_id` non corrisponde a una veste utilizzabile (spenta, fuori date, rapporto chiuso) | §8.3.4        |
| `E_CREDENZIALE_BLOCCATA`  | 403  | show_error_banner | Credenziale bloccata dall'amministratore: tutte le porte, non scade, il reset non la toglie | 2026-09-25 |
| `E_UTENTE_BLOCCATO`       | 403  | show_error_banner | Freno sulla **provenienza**: troppe password sbagliate di fila da questo IP (frase chiusa, i minuti restano nel contesto del DB) | Pre-esistente, per credenziale + provenienza dal 2026-09-25 |
| `E_LOGIN_ATTESA`          | 403  | show_error_banner | Attesa crescente sulla credenziale oltre il tetto di fallimenti da qualunque provenienza; i secondi nel `message` (⚠️ non in `detail`, che porta la causa del catalogo) | 2026-09-25 |
| `E_AUTH_CHIAMATA_NON_VALIDA` | 500 | show_error_banner | Provenienza (IP fidato) non ricavabile: il login si rifiuta prima di cercare lo username | 2026-09-25 |

La classe di ogni codice sta in `apps/core/services/error_policies_generated.py`
(`CLASSE_PER_CODICE`), i tre `redirect_login` in
`apps/core/services/error_ui_overrides.py`, i messaggi in
`apps/core/services/error_messages_fallback.py`.

> Il 401 da token scaduto o invalido (`InvalidToken` di SimpleJWT) esce
> nell'envelope come `E_AUTHENTICATION_FAILED` (E-3, chiuso 2026-09-27).
>
> I tre rifiuti della credenziale sono 403, non 429: il 429 e' il throttle
> per IP, che il frontend intercetta prima di leggere il codice. Modello
> delle tre regole: [guida multi-face §3.1-bis](../../../guide/architettura-multi-face-auth.md).

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
  **astratte**: registrarne una direttamente in una rotta fa sollevare
  `RuntimeError` al primo `post()` (guardia esplicita, non un `assert`).
  Usare SEMPRE le subclass namespace-specific.
- Il claim `sid` e' preservato da `SidTokenObtainPairSerializer`: il
  `MultiVesteTokenSerializer` eredita da Sid (non da `TokenObtainPairSerializer`
  diretto) — senza questa catena l'audit sessioni si romperebbe.
- Il throttle `LoginRateThrottle` (per IP; tasso da `DJANGO_API_LOGIN_THROTTLE_RATE`, default `5/5m`) e' applicato
  su **tutte e 3** le view di login (ereditato da `AuditTokenObtainPairView`).
  ⚠️ E' una regola diversa dal freno sulla provenienza (N password sbagliate
  sulla **stessa credenziale** dallo stesso IP): il throttle ferma chi inonda
  l'endpoint, il freno chi prova una credenziale.

## Dipendenze DB

| Tabella/Funzione                     | Schema        | Ruolo                                                                                                          |
| ------------------------------------ | ------------- | -------------------------------------------------------------------------------------------------------------- |
| `anagrafiche.identita_digitali`      | `anagrafiche` | Bridge auth_user ↔ soggetto_ruolo per veste. `UNIQUE(auth_user_id, ruolo_applicativo) WHERE attivo` post migration 20260420 |
| `django.auth_user`                   | `django`      | Credenziali                                                                                                    |
| `dbops.sessioni_utente`              | `dbops`       | Audit login/refresh                                                                                            |
| `script.fn_check_blocco_login`       | `script`      | Blocco dell'admin, freno per provenienza, attesa — prima della password                                        |
| `script.fn_registra_tentativo_login` | `script`      | Esito del tentativo per credenziale + provenienza                                                              |
| `script.fn_get_deve_cambiare_password` | `script`    | Cambio password obbligatorio della credenziale                                                                 |

## File backend

| File                                            | Ruolo                                                                                                                                                                                                                               |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/core/api/auth_views.py`                   | `AuditTokenObtainPairView` (astratta) + 3 subclass login; `AuditTokenRefreshView` (astratta) + 3 subclass refresh; helper `_extract_identita_id_from_refresh`, `_decode_refresh_payload` (claim per audit e GUC, dopo la validazione); la veste del guard da `claims_refresh_firmati` di `refresh_cookie.py` |
| `apps/core/api/multi_veste_token_serializer.py` | `MultiVesteTokenSerializer` + 3 subclass (Admin/Portale/Shop), `VesteNonAttivaError`                                                                                                                                                |
| `apps/core/api/jwt_audit_authentication.py`     | `JwtAuditAuthentication` (legge claim + popola GUC), `set_jwt_gucs`, `JwtSenzaIdentitaError`, `IdentitaNonAttivaError`                                                                                                              |
| `apps/core/api/token_serializers.py`            | `SidTokenObtainPairSerializer` (parent di MultiVeste, aggiunge `sid`)                                                                                                                                                               |
| `apps/core/db/auth_repository.py`               | `find_veste_utilizzabile_per_ruoli`, `get_veste_utilizzabile`, `get_identita_dettaglio`, `check_blocco_login`, `registra_tentativo_login`, `get_deve_cambiare_password`                                                                                          |
| `apps/core/services/auth_constants.py`          | Costanti `JWT_CLAIM_*` + `RUOLO_APPLICATIVO_*`                                                                                                                                                                                      |
| `apps/core/services/error_policies_generated.py` | Classe di `E_VESTE_NON_ATTIVA`, `E_JWT_SENZA_IDENTITA`, `E_JWT_SENZA_SID`, `E_IDENTITA_NON_ATTIVA` (`CLASSE_PER_CODICE`)                                                                                                             |
| `apps/core/api/error_responses.py`              | `drf_exception_handler` — priorita' a `default_code` E_* delle subclass AuthenticationFailed                                                                                                                                        |
| `backend/zeroerp_backend/urls.py`               | 9 route registrate: 3 login, 3 refresh, 3 `token/secondo-fattore/`                                                                                                                                                                                                            |

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
