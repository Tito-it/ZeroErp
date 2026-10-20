# Auth Views Audit (Core Django)

## Scopo

Override delle view SimpleJWT per agganciare: (a) l'audit login/refresh nella
tabella `dbops.sessioni_utente`, (b) lo stato della credenziale — blocco
dell'admin, freno per provenienza, attesa crescente —, (c) il throttle IP, (d) il guard cross-namespace multi-veste (§8.3).

Per il **contratto HTTP completo** dei 6 endpoint (3 login + 3 refresh, uno
per namespace), i claim JWT custom e i codici errore → vedi
[api_multi_veste_token.md](api_multi_veste_token.md). Questo documento
descrive l'architettura interna delle view.

## Contesto

File `apps/core/api/auth_views.py`. Post refactor multi-face §8.3, le view di
login/refresh sono organizzate in **2 classi base astratte** + **6 subclass
namespace-specific**.

### Gerarchia delle classi

```text
TokenObtainPairView  (SimpleJWT)
  └── AuditTokenObtainPairView       [ASTRATTA]  audit + throttle + blocco
        ├── AdminTokenView           → /api/v1/admin/token/    (OPERATORE)
        ├── PortaleTokenView         → /api/v1/portale/token/  (CLIENTE/FORNITORE_PORTALE)
        └── ShopTokenView            → /api/v1/shop/token/     (SHOP_CUSTOMER)

TokenRefreshView  (SimpleJWT)
  └── AuditTokenRefreshView          [ASTRATTA]  audit + guard cross-namespace
        ├── AdminTokenRefreshView    → /api/v1/admin/token/refresh/
        ├── PortaleTokenRefreshView  → /api/v1/portale/token/refresh/
        └── ShopTokenRefreshView     → /api/v1/shop/token/refresh/
```

### `AuditTokenObtainPairView` (base astratta)

- **Astratta**: `serializer_class = None` + guardia esplicita in `post()`:
  usata senza subclass, il primo `post()` solleva `RuntimeError`. Le subclass DEVONO fornire
  un `serializer_class` sottoclasse di `MultiVesteTokenSerializer`.
- **Throttle**: `LoginRateThrottle` (5 richieste / 5 minuti per IP) — contro
  chi **inonda** l'endpoint, qualunque credenziale provi. ⚠️ E' una regola
  diversa dal freno qui sotto, anche se i numeri si somigliano.
- **Provenienza**: prima di tutto, l'IP fidato del chiamante
  (`get_client_ip`). Se non si ricava, il login si rifiuta con
  `E_AUTH_CHIAMATA_NON_VALIDA` (500) **prima** di cercare lo username: la
  risposta non dice se l'utente esiste, e il DB non riceve mai una provenienza
  `NULL`.
- **Nome tentato**: lo username si legge **dal campo del serializer**
  (`_nome_tentato`), cioè già normalizzato come lo vedrà `authenticate`
  (spazi tolti, numeri convertiti). Con quel valore si cerca la credenziale
  (`_find_user`, uguaglianza esatta come `ModelBackend`) e se ne calcola
  l'impronta (`nome_tentato.digest_nome_tentato`, HMAC-SHA256 con chiave del
  backend, 32 byte). ⛔ Fino al 2026-09-25 il lookup usava il valore grezzo:
  con « tid» non trovava la credenziale e blocco, freno e attesa non si
  controllavano, mentre `authenticate("tid")` faceva entrare. Un nome
  assente, vuoto o non testuale non è un tentativo: il serializer risponde
  400 senza guardare la password, e il DB non viene chiamato.
- **Stato della credenziale** (contro chi **prova** una credenziale):
  `AuthRepository.check_blocco_login(uid | None, nome_digest=, provenienza=)`
  solleva dal DB, nell'ordine, `E_CREDENZIALE_BLOCCATA` (blocco dell'admin),
  `E_UTENTE_BLOCCATO` (freno su questa provenienza), `E_LOGIN_ATTESA`
  (attesa crescente) — tutti 403. ⭐ Si chiama **sempre**, anche per un nome
  che non trova una credenziale (R-7): allora `uid` è `None` e il DB usa
  l'impronta del nome come chiave (`config.nomi_tentati`), con gli stessi
  numeri e le stesse frasi. Chi prova non capisce se il nome esiste. Modello:
  [guida multi-face §3.1-bis](../../../guide/architettura-multi-face-auth.md)
  e [fn_check_blocco_login](/dbzero/script/manual/fn_check_blocco_login).
- **Esito**: `registra_tentativo_login(uid | None, nome_digest=, provenienza=, successo=)` —
  fallimento: conta sulla coppia e sulla chiave (credenziale o nome);
  successo: azzera la credenziale e la **sola** coppia da cui si e' entrati
  (un successo ha sempre la credenziale). Eccezione:
  `VesteNonAttivaError` (credenziali OK ma veste sbagliata) NON conta.
  ⛔ Il fallimento si intercetta su `rest_framework.exceptions.AuthenticationFailed`
  (quello che solleva il serializer), **non** sulla classe omonima di
  SimpleJWT, che ne e' una sottoclasse: fino al 2026-09-25 l'import era
  quello, e nessuna password sbagliata arrivata dall'API veniva contata.
- **Audit login**: dopo login OK, popola le GUC di sessione via
  `set_jwt_gucs(username=, user_id=, identita_id=, request=)` (l'`identita_id`
  e' estratto dal refresh appena emesso tramite `_extract_identita_id_from_refresh`;
  al login `emittente_attivo_id` non viene passato, quindi
  `app.current_emittente_id` resta vuota durante la scrittura dell'audit),
  poi chiama `session_audit_service.record_login(user_id=, request=, jti=)`.
  Il valore passato come `jti` e' il claim `sid` del refresh (`_extract_claims`).
- **Flag password_change_required**: se
  `AuthRepository.get_deve_cambiare_password(user.id)` ritorna True (l'obbligo
  e' della **credenziale**, vale su ogni porta), aggiunge
  `password_change_required: true` alla response.

### Subclass login (Admin/Portale/Shop)

Differiscono dalla base SOLO per `serializer_class`:

- `AdminTokenView.serializer_class = AdminTokenSerializer` (veste `OPERATORE`)
- `PortaleTokenView.serializer_class = PortaleTokenSerializer` (vesti portale)
- `ShopTokenView.serializer_class = ShopTokenSerializer` (veste `SHOP_CUSTOMER`)

Il serializer concreto (subclass di `MultiVesteTokenSerializer`) risolve
l'identita attiva dell'utente con `ruolo_applicativo` nel subset ammesso e
inietta i claim `identita_id` + `ruolo_applicativo` nel JWT. Se l'utente
non ha la veste richiesta dal namespace → `VesteNonAttivaError` (403).

### `AuditTokenRefreshView` (base astratta)

- **Astratta**: `expected_ruoli_applicativi = ()` + guardia esplicita in
  `post()`: usata senza subclass, il primo `post()` solleva `RuntimeError`.
- **Refresh dal cookie**: il refresh non si legge dal corpo ma dal cookie
  HttpOnly `zeroerp_refresh` (BB `refresh_cookie.py`, dal 2026-09-28). Prima
  di tutto `richiedi_header_anti_csrf` pretende `X-Requested-With:
  XMLHttpRequest` (403 `E_PERMISSION_DENIED`): e' l'unica richiesta
  autenticata dal solo cookie. Poi `leggi_refresh_cookie`: senza cookie →
  `InvalidToken` (401 `E_AUTHENTICATION_FAILED`).
- **Guard cross-namespace**: legge il claim `ruolo_applicativo` da claim con
  la **firma verificata** (`claims_refresh_firmati`, vedi la voce «Veste dal
  token verificato») e rifiuta con `VesteNonAttivaError` (403) se il claim
  manca o non rientra in `expected_ruoli_applicativi`. Il guard gira **prima**
  di `_rinnova`, che ruoterebbe e metterebbe in blacklist il token: un refresh
  del canale sbagliato non si brucia.
- **`_rinnova`**: il corpo di `TokenViewBase.post` col refresh preso dal
  cookie — stessa validazione (firma, scadenza, blacklist, rotazione) e stessa
  traduzione di `TokenError` in `InvalidToken` (401). Il refresh ruotato esce
  dal corpo e va nel `Set-Cookie` (`sposta_refresh_nel_cookie`).
- **Veste dal token verificato** (E-8, chiuso 2026-09-28): prima del guard
  cross-namespace i claim si leggono con la **firma verificata** (BB
  `claims_refresh_firmati` di `refresh_cookie.py`, lo stesso del logout). Un
  refresh illeggibile o non emesso da questo backend → 401; un refresh nostro
  senza claim `ruolo_applicativo` o di un altro canale → 403
  `E_VESTE_NON_ATTIVA`.
- **Audit refresh**: dopo refresh OK, legge `user_id` e `sid` dal refresh in
  entrata con decode non verificato (`_extract_claims`: il refresh e' gia'
  blacklistato dalla rotation, `RefreshToken(...)` fallirebbe), risolve lo
  username (`_resolve_username`), popola le GUC con `set_jwt_gucs` passando
  `identita_id` **e** `emittente_attivo_id` presi dallo stesso refresh, poi
  chiama `session_audit_service.record_refresh`.
- **Claim preservation**: SimpleJWT con `ROTATE_REFRESH_TOKENS=True` ruota
  solo `jti/exp/iat`; i claim custom (`identita_id`, `ruolo_applicativo`,
  `sid`, `emittente_attivo_id` se presente) sono preservati nel nuovo refresh.

### Subclass refresh (Admin/Portale/Shop)

Differiscono dalla base SOLO per `expected_ruoli_applicativi`:

- `AdminTokenRefreshView.expected_ruoli_applicativi = ("OPERATORE",)`
- `PortaleTokenRefreshView.expected_ruoli_applicativi = ("CLIENTE_PORTALE", "FORNITORE_PORTALE")`
- `ShopTokenRefreshView.expected_ruoli_applicativi = ("SHOP_CUSTOMER",)`

## Input

Vedi [api_multi_veste_token.md](api_multi_veste_token.md) §Input. Il login
admin vuole `{username, password}`; i login portale e shop si fanno con
l'**email**: `{email, password}`. I 3 refresh
hanno corpo vuoto, leggono il refresh dal cookie `zeroerp_refresh` e
pretendono l'header `X-Requested-With: XMLHttpRequest`.

## Output

Corpo `access` (+ eventuale `password_change_required` al login); il refresh
non sta mai nel corpo ma nel `Set-Cookie` `zeroerp_refresh` (attributi in
[api_multi_veste_token.md](api_multi_veste_token.md#cookie-di-refresh)). Al
login lo sposta `sposta_refresh_nel_cookie` come **ultimo** passo di
`AuditTokenObtainPairView.post`, dopo l'audit e le GUC che leggono ancora i
claim dal refresh nel corpo. Il JWT contiene i claim custom
(`identita_id`, `ruolo_applicativo`, `sid`, e `emittente_attivo_id` quando
l'utente ha un emittente attivo) documentati in
[api_multi_veste_token.md](api_multi_veste_token.md) §Claim JWT custom.

**Secondo fattore attivo**: se la credenziale ha un device TOTP attivo, la
password giusta non basta e il login risponde **200 senza token ne' cookie**:

```json
{ "two_factor_required": true, "sfida": "<sfida firmata>", "scade_in_secondi": 300 }
```

L'accesso si chiude con `POST /api/v1/{admin|portale|shop}/token/secondo-fattore/`
(sfida + codice), che emette `access` e cookie come il login a un passo.
Nessuna sessione e nessun successo sul freno al primo passo.

**Effetto aggiuntivo**: INSERT in `dbops.sessioni_utente` (audit login/refresh).

## Regole

- Il logging sessione avviene **solo** dopo risposta con successo (status 200).
  Login/refresh falliti non generano record.
- `VesteNonAttivaError` al login e' catturato prima di
  `AuthenticationFailed` per **non** incrementare tentativi falliti (no
  autoblock su errore "canale sbagliato").
- `set_jwt_gucs` ritorna `False` se `identita_id` e' None, se l'identita
  non e' attiva o se la query fallisce (`DatabaseError`): in quel caso viene loggato `security.{login,refresh}_guc_mancate`
  e l'audit procede con GUC vuote (user_insert='zeroerp_app').
- Le 6 view concrete sono registrate in `zeroerp_backend/urls.py` con
  `permission_classes=[AllowAny]` (endpoint pubblici di autenticazione),
  accanto alle 3 del secondo passo (`…/token/secondo-fattore/`).
- **Breaking change §8.3.1**: il path legacy `/api/v1/auth/token/` e'
  stato rimosso senza alias. Client pre-refactor devono essere aggiornati.

## Dipendenze

| Componente                           | Ruolo                                                           |
| ------------------------------------ | --------------------------------------------------------------- |
| `dbops.sessioni_utente`              | INSERT via `session_audit_service` (login/refresh/logout)       |
| `anagrafiche.identita_digitali`      | Source di `identita_id` + `ruolo_applicativo` iniettati nel JWT |
| `script.fn_check_blocco_login`       | Blocco, freno per provenienza, attesa — prima della password    |
| `script.fn_registra_tentativo_login` | Esito del tentativo per credenziale (o nome tentato) + provenienza |
| `nome_tentato.digest_nome_tentato` / `etichetta_log` | Impronta del nome tentato (HMAC, la chiave non va al DB); come il tentativo compare nei log |
| `script.fn_get_deve_cambiare_password` | Cambio password obbligatorio della credenziale                |
| `MultiVesteTokenSerializer`          | Iniezione claim custom + risoluzione veste                      |
| `JwtAuditAuthentication`             | Validazione claim + popolamento GUC a ogni request              |

## Test

- `apps/core/tests/api/test_auth_views.py` — test behavior login/refresh,
  guard astratta, cross-namespace (Admin/Portale/Shop), no-tentativo su
  `VesteNonAttivaError`, provenienza assente, extract helpers; nome
  inesistente sulle stesse due chiamate e mai in chiaro nei log, nome con
  spazi normalizzato come `authenticate`, nome assente senza chiamate al DB.
- `apps/core/tests/db/test_login_credenziale_db.py` — ⭐ sul DB vero
  (`ZEROERP_TEST_DB_E2E=1`): binding di `AuthRepository` e login vero dalla
  view — 401 che contano, freno 403 solo dalla provenienza che sbaglia,
  attesa coi secondi nel `message`, login riuscito; ⭐ la parità del nome
  inesistente (stesse risposte di una credenziale vera) e il freno che non
  si aggira con uno spazio davanti al nome.
- `apps/core/tests/api/test_multi_veste_token_serializer.py` — test serializer,
  `VesteNonAttivaError`, claim injection.
- `apps/core/tests/api/test_jwt_audit_authentication.py` — test authenticate
  multi-face (`E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA`, CTE GUC).

## Note di migrazione

- Le view base `AuditTokenObtainPairView` / `AuditTokenRefreshView`
  sostituiscono `TokenObtainPairView` / `TokenRefreshView` nel routing
  **tramite subclass concrete**, mai direttamente.
- Pre-§8.3: esistevano solo 2 route (`/auth/token/` + `/auth/token/refresh/`)
  sulla base, senza guard cross-veste, senza claim custom.
- Post-§8.3: 6 route + claim custom + guard cross-namespace + audit
  identita-aware. Il contratto HTTP esterno resta compatibile con client
  SimpleJWT standard (stesso input/output base), ma:
  1. I client devono aggiornarsi al nuovo path (`/admin/` etc.).
  2. Il JWT contiene claim aggiuntivi — ignorati dai consumer che non li
     leggono, letti da `/me/` e `JwtAuditAuthentication`.

## Documenti correlati

- [api_multi_veste_token.md](api_multi_veste_token.md) — contratto HTTP
  completo 6 endpoint + claim + error codes
- [api_user_profile.md](api_user_profile.md) — `/me/` espone `identita`
- [api_logout.md](api_logout.md) — logout + blacklist refresh
- [api_token_cambio_password.md](api_token_cambio_password.md) — cambio password
