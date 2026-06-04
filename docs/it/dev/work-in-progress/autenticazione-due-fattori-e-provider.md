# Autenticazione — 2FA TOTP e provider esterni (OAuth) — WIP

> Documento di pianificazione per l'estensione del sistema di autenticazione.
>
> **Data creazione originale**: 2026-04-01 (solo 2FA TOTP)
> **Rinominato e aggiornato**: 2026-04-23 — aggiunto piano OAuth/SSO + riallineamento al modello multi-face corrente
> **Stato**: **PIANIFICATO — non ancora in sviluppo**
> **Rinomina da**: `autenticazione-due-fattori.md` → `autenticazione-due-fattori-e-provider.md`
>
> Copertura:
>
> * **Parte A**: 2FA TOTP (Google Authenticator, Authy)
> * **Parte B**: Autenticazione tramite provider esterni (Google, Microsoft, Apple, ecc.)
>
> Entrambe estendono il medesimo flusso login esistente e condividono il modello
> identità digitali. Si trattano insieme per evitare drift architetturale.

---

## 0. Premessa — stato autenticazione corrente (allineamento 2026-04-23)

Situazione registrata dopo il refactor **multi-face auth** (§8.3.x), completato con `dev/db-tid` 2026-04-18/20.

### 0.1 Modello identità

- **`auth_user` Django** = credenziali password + email + username (1 record per persona fisica)
- **`anagrafiche.identita_digitali`** = bridge N:M verso `soggetti_ruoli`, **una riga per ogni ruolo applicativo attivo** (vincolo UNIQUE `uq_identita_digitali_auth_user_ruolo_attivo` su `(auth_user_id, ruolo_applicativo) WHERE attivo`)
- **`anagrafiche.risorse_umane_auth_user`** = ponte RU ↔ auth_user per operatori interni (1:1 auth_user↔RU); **tabella legacy rispetto al modello multi-face** ma ancora attiva per compatibilità
- Ruoli applicativi (enum): `OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`, `API_CLIENT`, `DISABILITATO`

### 0.2 Dove vivono i flag auth (importante per il piano sotto)

Campi rilevanti **per auth** presenti su entrambe le tabelle a seguito del refactor:

| Campo                    | `risorse_umane_auth_user` | `identita_digitali` | Canonico post-multi-face         |
| ------------------------ | :-----------------------: | :-----------------: | -------------------------------- |
| `deve_cambiare_password` |             ✅            |          ✅         | `identita_digitali` (per-veste)  |
| `tentativi_falliti`      |             ✅            |          ✅         | `identita_digitali`              |
| `bloccato_fino_a`        |             ✅            |          ✅         | `identita_digitali`              |
| `totp_obbligatorio`      |             ✅            |          ✅         | `identita_digitali` (per-veste)  |
| `invito_inviato_at`      |             ✅            |          ✅         | `identita_digitali`              |

**Implicazione operativa**: la fonte di verità per i flag per-identità è `identita_digitali`. Per un utente con N vesti (es. OPERATORE + CLIENTE_PORTALE) il 2FA può essere obbligatorio su una veste e opzionale sull'altra. Il device TOTP, invece, è **1:1 per auth_user** (una sola persona fisica, una sola app authenticator), cfr. §A.1.

### 0.3 Login attuale (3 canali)

- `POST /api/admin/token/` → ruoli `OPERATORE`, `API_CLIENT`
- `POST /api/portale/token/` → `CLIENTE_PORTALE`, `FORNITORE_PORTALE`
- `POST /api/shop/token/` → `SHOP_CUSTOMER`

Tutti generati da `SidTokenObtainPairSerializer` ([token_serializers.py](../../../../backend/apps/core/api/token_serializers.py)) con claim JWT:

- `user_id` (SimpleJWT standard)
- `identita_id` (§8.3.2 — obbligatorio, altrimenti `E_JWT_SENZA_IDENTITA`)
- `ruolo_applicativo`
- `sid` (session ID stabile, persiste al refresh rotation)

Propagazione DB via `set_jwt_gucs()` in [jwt_audit_authentication.py](../../../../backend/apps/core/api/jwt_audit_authentication.py): 5 GUC `app.*` session-scoped popolate in singola query CTE dopo ogni `authenticate()` riuscito. Vedi `risorse-umane-e-accessi.md` §"Propagazione identità utente al database (GUC)".

### 0.4 Cosa ancora NON c'è

- 2FA TOTP → tabella `config.auth_totp_device` creata (20260328-20), ma nessun flusso BE/FE
- Provider esterni (OAuth/OIDC) → nessuna dipendenza, nessuna tabella, nessun endpoint
- Magic link senza password → fuori scope qui
- WebAuthn/Passkey → fuori scope, possibile evoluzione futura

---

# Parte A — 2FA TOTP

## A.1 DB (stato)

### A.1.1 Tabella `config.auth_totp_device` — CREATA ✅ (20260328-20)

Stato effettivo come da [doc tabella](../../dbzero/config/tabelle/auth_totp_device):

```
config.auth_totp_device
├── id                  BIGSERIAL PK
├── auth_user_id        INTEGER UNIQUE NOT NULL FK → auth_user(id)
│                       (1:1 — un solo device TOTP per persona fisica,
│                        condiviso tra tutte le vesti/identita' di quell'auth_user)
├── secret_encrypted    VARCHAR(512) NOT NULL
│                       (secret TOTP crittografato con Fernet/SECRET_KEY)
├── abilitato           BOOLEAN NOT NULL DEFAULT false
├── confermato          BOOLEAN NOT NULL DEFAULT false
│                       (true solo dopo prima verifica riuscita)
├── recovery_codes_hash JSONB NOT NULL DEFAULT '[]'
│                       (array di hash SHA-256 dei codici recovery)
├── ultimo_codice_usato VARCHAR(10) NULL
│                       (anti-replay: ultimo codice TOTP verificato)
├── ultimo_uso_at       TIMESTAMPTZ NULL
├── meta                JSONB NOT NULL DEFAULT '{}'
└── audit fields (data_insert, user_insert, data_update, user_update)
```

**Scelta architetturale**: device 1:1 per `auth_user`, non per identità. Una persona fisica ha una sola app authenticator sul telefono; il 2FA la autentica come persona, poi il login sceglie la veste (claim `identita_id` nel JWT). La forzatura del 2FA (`totp_obbligatorio`) è invece per-veste.

### A.1.2 Colonne `totp_obbligatorio` — CREATE ✅

- `risorse_umane_auth_user.totp_obbligatorio` — aggiunta ✅ (20260328-21). Copre solo operatori; **conservata per compatibilità** ma non è la fonte canonica.
- `identita_digitali.totp_obbligatorio` — presente (post-refactor multi-face, deriva da migrations `20260418-10+`). **Fonte canonica**: copre tutte le vesti (OPERATORE, CLIENTE_PORTALE, FORNITORE_PORTALE, SHOP_CUSTOMER).

**Nota implementativa**: il middleware 2FA (§A.4.8) deve controllare `identita_digitali.totp_obbligatorio` sull'identità del JWT corrente, non `risorse_umane_auth_user`. La colonna legacy su `risorse_umane_auth_user` è utile solo se un admin setta il flag "su tutti gli operatori" come policy aziendale: va mantenuta sincronizzata con l'identità OPERATORE via trigger o applicativo (vedi §A.2.3 — brief DB).

### A.1.3 Da fare — DB

- [ ] **A.1.3.a** — Aggiornare `script.fn_get_user_profile()` ([fn_get_user_profile](../../dbzero/script/funzioni/fn_get_user_profile)) per includere nel JSONB di risposta:
  - `totp_abilitato` — da `auth_totp_device` (EXISTS con `abilitato=true AND confermato=true`)
  - `totp_obbligatorio` — **da `identita_digitali`** per l'identità del JWT corrente (non da `risorse_umane_auth_user`)
  - Il manual `fn_get_user_profile_auth_flags.md` oggi documenta solo `deve_cambiare_password`: estendere con le due chiavi TOTP.
- [ ] **A.1.3.b** *(opzionale, consigliato)* — **Trigger di sync legacy→canonico**: `trgfn_risorse_umane_auth_user_sync_totp_obbligatorio` che propaga `totp_obbligatorio` su `identita_digitali` per l'identità `ruolo_applicativo='OPERATORE'` attiva. Evita la divergenza tra le due tabelle finché `risorse_umane_auth_user.totp_obbligatorio` non viene deprecato.

## A.2 Backend

### A.2.1 `TotpService` — `apps/core/services/totp_service.py`

- [ ] **A.2.1** — Creare servizio. Responsabilità:
  - `setup_device(auth_user_id) → {secret, provisioning_uri, qr_code_base64, recovery_codes}`
    - Genera secret con `pyotp.random_base32()`
    - Cifra secret con Fernet usando `SECRET_KEY`
    - Genera 10 recovery codes (16 char hex), salva SHA-256 dei codici (mai in chiaro)
    - Ritorna recovery codes in chiaro **una sola volta** (unica occasione di lettura)
  - `confirm_setup(auth_user_id, codice) → bool`
    - Verifica codice TOTP con `pyotp.TOTP(secret).verify(codice, valid_window=1)`
    - Se OK: `confermato=true`, `abilitato=true`
  - `verify(auth_user_id, codice) → {valido, tipo, recovery_rimanenti}`
    - Anti-replay: rifiuta se `codice == ultimo_codice_usato`
    - Prova TOTP → se fallisce prova match su hash recovery codes
    - Se match recovery: rimuovere hash dall'array (monouso)
    - Aggiorna `ultimo_codice_usato`, `ultimo_uso_at`
  - `disable(auth_user_id)`
    - Imposta `abilitato=false`, azzera secret e recovery codes
  - `regenerate_recovery_codes(auth_user_id, codice_totp) → [...]`
    - Verifica TOTP corrente (conferma possesso device), genera nuovi 10 codici

### A.2.2 Flusso login a due step

- [ ] **A.2.2** — Modifica Step 1 su tutti i 3 canali (`/api/admin/token/`, `/api/portale/token/`, `/api/shop/token/`):
  - Login username+password come ora
  - Dopo `authenticate()` successo, **prima di emettere il JWT definitivo**:
    - Risolve `identita_id` (come oggi in `MultiVesteTokenSerializer` §8.3.2)
    - Se esiste riga in `auth_totp_device` con `abilitato=true AND confermato=true` **oppure** `identita_digitali.totp_obbligatorio=true` per la veste scelta:
      - NON emette JWT
      - Ritorna `{ two_factor_required: true, two_factor_token: "<token>" }`
      - Il `two_factor_token` è un token firmato con Django `TimestampSigner` (scadenza 5 minuti) che porta `{auth_user_id, identita_id, canale}`
    - Altrimenti: flusso JWT normale
- [ ] **A.2.3** — Nuovo endpoint step 2: `POST /api/{canale}/token/2fa-verify/`
  - Input: `{ two_factor_token, code }`
  - Valida firma/scadenza `two_factor_token`
  - Chiama `TotpService.verify(auth_user_id, code)`
  - Se OK: emette JWT con `identita_id` già risolto nel token temporaneo (evita seconda risoluzione veste)
  - Se recovery code: accetta, decrementa, eventualmente ritorna warning "ti restano N codici"
  - Log tentativi su `dbops.sessioni_utente.meta` (già esistente)

### A.2.4 Endpoint profilo 2FA (self-service)

- [ ] **A.2.4** — `POST /api/v1/auth/2fa/setup/` — avvia setup, ritorna QR code + secret base32 + recovery codes (1 volta)
- [ ] **A.2.5** — `POST /api/v1/auth/2fa/confirm/` — conferma setup (primo codice TOTP valido)
- [ ] **A.2.6** — `POST /api/v1/auth/2fa/disable/` — disabilita 2FA (richiede password corrente). Blocca se esiste identità con `totp_obbligatorio=true` su qualche veste attiva.
- [ ] **A.2.7** — `POST /api/v1/auth/2fa/recovery-codes/` — rigenera 10 nuovi codici (richiede codice TOTP valido)

### A.2.5 Endpoint admin per gestione 2FA operatori

- [ ] **A.2.8** — `DELETE /api/v1/amm-software/operatori/<id>/2fa/` — disable emergenza (admin)
- [ ] **A.2.9** — `PUT /api/v1/amm-software/operatori/<id>/2fa-obbligatorio/` — imposta/rimuove obbligo. **Opera su `identita_digitali.totp_obbligatorio` per la veste OPERATORE** (non su `risorse_umane_auth_user`, cfr. §0.2).
- [ ] **A.2.10** — Audit log per ogni operazione admin su 2FA (usa `dbops.error_log` o `event_log` con severity INFO)

### A.2.6 Middleware 2FA obbligatorio

- [ ] **A.2.11** — Nuovo middleware `TotpRequiredMiddleware` (dopo `JwtAuditMiddleware`, prima di `PasswordChangeRequiredMiddleware`):
  - Se `identita_digitali.totp_obbligatorio=true` **e** `auth_totp_device.abilitato=false`:
    - Consente solo: `/auth/2fa/setup/`, `/auth/2fa/confirm/`, `/auth/logout/`, `/core/me/`
    - Tutti gli altri → 403 `E_2FA_SETUP_RICHIESTO`
  - Check GUC-first: legge `app.current_identita_id` già in GUC (niente query extra)

## A.3 Frontend

- [ ] **A.3.1** — `LoginView.vue` (+ varianti portale/shop): flusso a due step
  - Step 1: username + password come ora
  - Se response `two_factor_required=true` → mostra input 6-cifre + link "Usa codice di recupero"
  - Step 2: POST `/token/2fa-verify/` con `{ two_factor_token, code }`
- [ ] **A.3.2** — Nuova sezione "Sicurezza" nel profilo utente (pagina `/me/sicurezza`):
  - Stato 2FA: Abilitato / Disabilitato / Obbligatorio non configurato
  - Wizard setup:
    1. QR code + secret testuale (per input manuale)
    2. Input codice di conferma
    3. Lista recovery codes (download `.txt` + pulsante stampa)
    4. Checkbox "Ho salvato i codici"
  - Pulsanti "Disabilita 2FA" (richiede password) e "Rigenera recovery codes" (richiede codice TOTP)
- [ ] **A.3.3** — Drawer operatore (admin) — aggiungere:
  - Badge "2FA attivo" / "Non configurato" / "Obbligatorio"
  - Pulsante "Disabilita 2FA" (emergenza, con `useConfirmAction`)
  - Toggle "2FA obbligatorio" → chiama `PUT .../2fa-obbligatorio/`
- [ ] **A.3.4** — Route guard "forzato setup 2FA": se `totp_obbligatorio && !totp_abilitato` → redirect a `/me/sicurezza/setup-2fa` (simile a `PasswordChangeRequiredGuard`)

## A.4 Test

- [ ] **A.T.1** — `TotpService.setup_device()` → secret + QR + recovery codes
- [ ] **A.T.2** — `TotpService.confirm_setup()` con codice valido
- [ ] **A.T.3** — Login 2-step completo su canale ADMIN
- [ ] **A.T.4** — Anti-replay (stesso codice rifiutato consecutivamente)
- [ ] **A.T.5** — Recovery code valido: decremento contatore, hash rimosso
- [ ] **A.T.6** — Admin disabilita 2FA operatore (audit log presente)
- [ ] **A.T.7** — `TotpRequiredMiddleware` blocca quando `totp_obbligatorio && !abilitato`
- [ ] **A.T.8** — Multi-veste: stessa persona ha 2FA obbligatorio su OPERATORE e opzionale su CLIENTE_PORTALE → login sui due canali comportamento diverso

## A.5 Dipendenze Python

| Pacchetto | Versione | Scopo                                                |
| --------- | -------- | ---------------------------------------------------- |
| `pyotp`   | >= 2.9   | Generazione/verifica codici TOTP                     |
| `qrcode`  | >= 8.0   | QR code per setup authenticator                      |
| `Pillow`  | >= 11.0  | Output immagine (dipendenza di `qrcode`)             |

Aggiungere a `backend/requirements.in` e rigenerare `requirements.txt` con `pip-compile` (cfr. AGENTS.md §"Versione Python").

---

# Parte B — Autenticazione tramite provider esterni (OAuth/OIDC)

## B.1 Obiettivo e scope

Consentire il login su uno o più canali (ADMIN/PORTALE/SHOP) tramite provider OAuth/OIDC esterni: **Google**, **Microsoft**, **Apple**, estendibile ad altri (GitHub, LinkedIn, provider aziendali custom tipo Okta/Azure AD tenant).

**Invariante**: l'autenticazione esterna produce lo **stesso JWT interno** del password flow — claim `identita_id`, `ruolo_applicativo`, `sid`. I permessi, il middleware GUC, il route guard frontend **non cambiano**.

## B.2 Schema DB proposto

### B.2.1 Nuova tabella `config.identita_provider_mapping`

- [ ] **B.2.1** — Brief al team DB per creare:

```sql
CREATE TABLE config.identita_provider_mapping (
    id                   BIGSERIAL PRIMARY KEY,
    identita_digitale_id BIGINT NOT NULL
        REFERENCES anagrafiche.identita_digitali(id) ON DELETE CASCADE,
    provider             VARCHAR(50) NOT NULL,   -- 'google', 'microsoft', 'apple'
    provider_sub         VARCHAR(500) NOT NULL,  -- subject claim dell'IdP (stabile per provider)
    provider_email       VARCHAR(254),           -- email al momento del linking (denorm per audit)
    provider_name        VARCHAR(255),           -- display name (denorm per audit)
    attivo               BOOLEAN NOT NULL DEFAULT true,
    linked_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_login_at      TIMESTAMPTZ,
    meta                 JSONB NOT NULL DEFAULT '{}',
    data_insert          TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert          TEXT NOT NULL DEFAULT CURRENT_USER,
    data_update          TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_update          TEXT NOT NULL DEFAULT CURRENT_USER,
    tx_id                UUID,
    storicizza           BOOLEAN NOT NULL DEFAULT true
);

-- Invariante: per provider, un solo subject → una sola identità
ALTER TABLE config.identita_provider_mapping
  ADD CONSTRAINT uq_identita_provider_mapping_provider_sub
  UNIQUE (provider, provider_sub);

-- Indice di lookup al callback
CREATE INDEX ix_identita_provider_mapping_identita
  ON config.identita_provider_mapping(identita_digitale_id) WHERE attivo = true;
```

**Razionale**:

- **UNIQUE `(provider, provider_sub)`**: un account Google può essere collegato a una sola identità digitale. Evita shadow-linking.
- **`ON DELETE CASCADE`** sulla FK verso `identita_digitali`: se l'identità viene eliminata, il mapping esterno decade automaticamente.
- **Campi denorm (`provider_email`, `provider_name`)**: necessari per audit/UI (l'utente vede "Collegato a google:mario@example.com" nel profilo) e per GDPR (consent evidence).

### B.2.2 Colonne informative su `identita_digitali`

- [ ] **B.2.2** — Brief DB: aggiungere:

```sql
ALTER TABLE anagrafiche.identita_digitali ADD COLUMN
    login_methods TEXT[] NOT NULL DEFAULT ARRAY['PASSWORD']::TEXT[];
```

Valori ammessi nei membri dell'array: `'PASSWORD'`, `'OAUTH_GOOGLE'`, `'OAUTH_MICROSOFT'`, `'OAUTH_APPLE'`, ... (enum testuale estensibile).

Viene mantenuta sincronizzata da **trigger** su INSERT/UPDATE di `identita_provider_mapping.attivo`:

- [ ] **B.2.3** — Brief DB: trigger `trgfn_identita_provider_mapping_sync_methods` che:
  - su INSERT (attivo=true) o UPDATE (attivo false→true): aggiunge `'OAUTH_<PROVIDER>'` all'array (deduped)
  - su UPDATE (attivo true→false) o DELETE: rimuove il metodo
  - `'PASSWORD'` non viene toccato (è il metodo di default; si rimuove solo se admin lo revoca esplicitamente via endpoint dedicato, §B.4)

**Perché un trigger e non logica applicativa**: è un derived field che dipende da un'altra tabella; mantenerlo in DB evita drift se un'operazione di manutenzione DB crea/rimuove righe mapping senza passare dal BE.

### B.2.3 Vincolo: non lasciare l'identità senza metodo di login

- [ ] **B.2.4** — Brief DB: trigger `trgfn_identita_digitali_guard_login_methods`:
  - Blocca UPDATE su `identita_digitali` che porterebbe `login_methods=[]`
  - Errore `E_IDENTITA_SENZA_METODO_LOGIN`

Razionale: evitare che per errore un admin disabilita password + unlink di tutti i provider → utente bloccato fuori.

## B.3 Backend

### B.3.1 Dipendenze

- [ ] **B.3.1** — Aggiungere a `backend/requirements.in`:

| Pacchetto                      | Versione | Scopo                                                      |
| ------------------------------ | -------- | ---------------------------------------------------------- |
| `django-allauth`               | >= 0.57  | Framework OAuth multi-provider                             |
| `django-allauth[socialaccount]`| idem     | Estensione social providers                                |
| `requests-oauthlib`            | >= 1.3   | Client OAuth (dipendenza diretta per flussi custom)        |

`django-allauth` è preferito a `social-auth-app-django` perché:
- Mantenuto attivamente, RFC 6749/7636 compliant (supporto PKCE nativo)
- Hook espliciti (`SocialAccountAdapter.pre_social_login`, `populate_user`) per mappare il provider a `identita_digitali` senza forkare il flusso interno
- Abilita OIDC discovery out-of-the-box (endpoint `/.well-known/openid-configuration`)

### B.3.2 Configurazione

- [ ] **B.3.2** — `settings.py`:

```python
INSTALLED_APPS += [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.microsoft',
    'allauth.socialaccount.providers.apple',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ['OAUTH_GOOGLE_CLIENT_ID'],
            'secret':    os.environ['OAUTH_GOOGLE_CLIENT_SECRET'],
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    },
    'microsoft': {
        'APP': {
            'client_id': os.environ['OAUTH_MICROSOFT_CLIENT_ID'],
            'secret':    os.environ['OAUTH_MICROSOFT_CLIENT_SECRET'],
        },
        'TENANT': os.environ.get('OAUTH_MICROSOFT_TENANT', 'common'),
    },
    # Apple: richiede keypair JWT, vedi doc Apple Sign-In
}

# Custom adapter che mappa provider → identita_digitali
SOCIALACCOUNT_ADAPTER = 'apps.core.api.oauth_adapter.ZeroErpSocialAdapter'

# Disabilita l'auto-signup standard di allauth: vogliamo controllarlo noi
SOCIALACCOUNT_AUTO_SIGNUP = False
```

Secret management: chiavi in `.env` (dev) / secret manager (prod). **Mai committare client_secret.**

### B.3.3 Adapter custom — mapping provider → identità

- [ ] **B.3.3** — Creare `apps/core/api/oauth_adapter.py`:

```python
# Scopo: custom adapter che intercetta il callback OAuth riuscito,
#        mappa il provider_sub a un'identita_digitali esistente o la crea
#        (solo per canali self-service), poi genera il JWT ZeroErp al posto
#        della sessione django-allauth standard.
class ZeroErpSocialAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # 1. Estrai canale dalla request (path /api/admin/ vs /api/portale/ vs /api/shop/)
        # 2. Cerca in config.identita_provider_mapping (provider, sub)
        # 3a. Trovato + attivo + canale coerente → prepara JWT emission
        # 3b. Non trovato + canale in {PORTALE, SHOP} → crea auth_user + identita_digitali (self-service)
        # 3c. Non trovato + canale ADMIN → rifiuta (E_OAUTH_OPERATORE_NON_INVITATO)
        #     (gli operatori vengono invitati; il primo login OAuth collega l'identità
        #      creata dall'invito al provider_sub)
        # 4. Aggiorna ultimo_login_at, login_methods (via trigger), genera JWT
```

Il routing dei canali ai ruoli applicativi è lo stesso del password flow (mappa definita in `auth_constants.py` e già enforcata dai permission class):

| Canale callback      | Ruolo creabile         | Self-service? |
| -------------------- | ---------------------- | ------------- |
| `/api/admin/oauth/`   | `OPERATORE`            | ❌ (solo invito admin, poi linking al primo OAuth) |
| `/api/portale/oauth/` | `CLIENTE_PORTALE`, `FORNITORE_PORTALE` | ⚠️ opzionale (abilitabile via parameter) |
| `/api/shop/oauth/`    | `SHOP_CUSTOMER`        | ✅ |

### B.3.4 Endpoint OAuth per canale

- [ ] **B.3.4** — Nuovo blueprint `/api/{canale}/oauth/<provider>/`:
  - `GET  /api/{canale}/oauth/<provider>/authorize/` → redirect URL al provider (state + PKCE challenge generati server-side, salvati in Redis con TTL 10min sotto `oauth_state:<uuid>`)
  - `GET  /api/{canale}/oauth/<provider>/callback/?code=...&state=...` → exchange code, risolve identità, emette JWT ZeroErp
    - Se canale+identità richiedono 2FA (`identita_digitali.totp_obbligatorio=true` e device configurato), **applica step 2FA** dopo OAuth con stesso meccanismo di §A.2.2 (token temporaneo + `/2fa-verify/`)
  - `POST /api/{canale}/oauth/<provider>/link/` → **linking da utente già loggato** (aggiunge mapping al profilo corrente; richiede conferma OTP via email se password flow attivo, vedi §B.5)
  - `POST /api/v1/auth/oauth/<mapping_id>/unlink/` → unlink (admin o self). Blocca se `login_methods` sarebbe vuoto post-unlink (guard §B.2.3).

### B.3.5 Generazione JWT post-OAuth

- [ ] **B.3.5** — Estendere `SidTokenObtainPairSerializer` con metodo di classe `for_oauth_identita(identita_id, canale, provider) → token_pair`:
  - Stessa logica di risoluzione claim del password flow (chiama il codice esistente)
  - Aggiunge metadata di sessione su `dbops.sessioni_utente`: `metodo_login='oauth_<provider>'`
  - Incrementa `identita_provider_mapping.ultimo_login_at`

### B.3.6 Gestione 2FA post-OAuth (decisione di policy)

Due comportamenti possibili, **da decidere con stakeholder prima dello sprint**:

- **Opzione 1 (consigliata, default)**: 2FA sempre richiesto se `totp_obbligatorio=true`, anche dopo OAuth. Sicurezza massima.
- **Opzione 2**: trust provider MFA (se il provider dichiara MFA già fatto, es. Google con 2-step verification, saltare 2FA interno). Richiede inspection del claim `amr` (Authentication Methods Reference) OIDC. **Più complesso, richiede whitelist provider fidati.**

### B.3.7 Errori specifici

- [ ] **B.3.7** — Nuovi codici errore in `config.messaggi_errore`:
  - `E_OAUTH_STATE_INVALIDO` — state CSRF non trovato o scaduto
  - `E_OAUTH_CODE_SCAMBIO_FALLITO` — provider non ha risposto al code exchange
  - `E_OAUTH_PROVIDER_SUB_MANCANTE` — response provider senza subject claim
  - `E_OAUTH_EMAIL_NON_VERIFICATA` — provider non ha verificato l'email (Google: claim `email_verified=false`)
  - `E_OAUTH_OPERATORE_NON_INVITATO` — ADMIN callback senza identità pre-esistente invitata
  - `E_OAUTH_MAPPING_GIA_LINKATO` — tentativo di linking di un `provider_sub` già associato ad altra identità
  - `E_OAUTH_PROVIDER_DISABILITATO` — provider configurato ma feature flag OFF
  - `E_IDENTITA_SENZA_METODO_LOGIN` — tentativo unlink che lascerebbe l'identità senza metodo di accesso

## B.4 Frontend

### B.4.1 Pulsanti login sui tre canali

- [ ] **B.4.1** — `LoginView.vue` (admin), `PortaleLoginView.vue`, `ShopLoginView.vue`:
  - Sotto i campi username/password: sezione "Oppure accedi con"
  - Pulsanti configurati da config dinamica (`/api/{canale}/oauth/providers/`): mostra solo i provider effettivamente configurati per quel canale
  - Click → `window.location = /api/{canale}/oauth/<provider>/authorize/?redirect_uri=<current>` (flow redirect browser completo, non XHR)
  - Dopo callback il backend emette JWT e redirect a `/` con token in cookie temporaneo (o fragment URL), FE lo salva in localStorage come oggi

### B.4.2 Sezione "Account collegati" nel profilo

- [ ] **B.4.2** — Pagina `/me/sicurezza` (stessa di 2FA, sezione aggiuntiva):
  - Lista provider collegati (tabella: provider, email provider, linked_at, ultimo_login_at)
  - Pulsante "Collega Google/Microsoft/..." → avvia flow linking (§B.3.4 endpoint `/link/`)
  - Pulsante "Scollega" per ogni provider → chiama `/unlink/`. Warning se rimane solo PASSWORD e rimuovere renderebbe inaccessibile l'account.

### B.4.3 Drawer admin operatori: tab "Accessi"

- [ ] **B.4.3** — Estendere drawer operatore con tab "Accessi" (oppure sezione) che mostra:
  - Badge "Password" / "Google" / "Microsoft" / "2FA" per ogni identità dell'utente
  - Pulsante "Scollega provider" (emergency, admin only)

## B.5 Security — punti critici

### B.5.1 State CSRF e PKCE

- `state` random 32-byte URL-safe, salvato in Redis con TTL 10min, validato al callback. Binding a `session_id` per defense-in-depth.
- PKCE abilitato su tutti i provider che lo supportano (OAuth `OAUTH_PKCE_ENABLED: True`). Obbligatorio su Apple.

### B.5.2 Linking safety

**Scenario problematico**: Mario ha password su `mario@example.com`; qualcuno con accesso a Google Workspace crea `mario@example.com` e vuole collegarlo via OAuth. **Auto-linking su email** = account takeover.

**Decisione di policy**:
- **NON** auto-linkare per email. Il linking richiede sempre:
  - utente già loggato via password + conferma con OTP email (per evitare che il solo accesso alla sessione permetta di collegare un nuovo provider), **oppure**
  - in caso di primo login OAuth su canale ADMIN: fa match stretto su `identita_provider_mapping` pre-esistente (preparato dall'admin al momento dell'invito, via endpoint dedicato `/api/v1/amm-software/operatori/<id>/oauth-invite/`)

### B.5.3 Revoca provider-side

Se Google disabilita l'account di Mario, il JWT ZeroErp resta valido fino a scadenza (15min access / 24h refresh). Due opzioni:

- **B.5.3.a** (consigliato, sprint 2-3) — al refresh JWT, validare lato provider che il token sia ancora valido (solo se `grant_type=refresh_token` è supportato dal provider). Costo: +1 roundtrip per refresh.
- **B.5.3.b** (fuori scope MVP) — webhook provider → blacklist JWT in Redis. Solo alcuni provider supportano webhook di revoca (es. Google Security Events API, richiede setup complesso).

### B.5.4 Email non verificata

Se il provider non dichiara l'email verificata (`email_verified=false`), rifiutare il login con `E_OAUTH_EMAIL_NON_VERIFICATA`. Applicare a tutti i canali.

### B.5.5 GDPR

- [ ] **B.5.5** — Aggiornamenti documentali **non codice**:
  - Privacy policy: dichiarare quali dati provider sono memorizzati (`provider_sub`, `provider_email`, `provider_name`)
  - DPA con Google/Microsoft/Apple (obbligatorio in UE se si usa l'SDK del provider)
  - Consent evidence: `identita_provider_mapping.linked_at` + `meta.consent_text_version` (stringa del testo accettato al momento del linking)
  - Diritto all'oblio: DELETE del mapping (cascade cancella storico `storico_identita_provider_mapping` se abilitato)

## B.6 Test

- [ ] **B.T.1** — Callback Google mock: code exchange → identità esistente trovata → JWT emesso con claim corretti
- [ ] **B.T.2** — Callback canale ADMIN senza identità invitata → `E_OAUTH_OPERATORE_NON_INVITATO`
- [ ] **B.T.3** — State CSRF scaduto → `E_OAUTH_STATE_INVALIDO`
- [ ] **B.T.4** — Email non verificata → `E_OAUTH_EMAIL_NON_VERIFICATA`
- [ ] **B.T.5** — Linking da utente loggato: OTP richiesto, validato, mapping creato
- [ ] **B.T.6** — Unlink ultimo metodo → `E_IDENTITA_SENZA_METODO_LOGIN` (trigger DB)
- [ ] **B.T.7** — 2FA post-OAuth: `totp_obbligatorio=true` → callback emette `two_factor_token`, non JWT
- [ ] **B.T.8** — Multi-canale: stesso `provider_sub` non può essere linkato a due identità diverse (UNIQUE constraint DB)

## B.7 Dipendenze e infrastruttura

- **Variabili ambiente**:
  ```
  OAUTH_GOOGLE_CLIENT_ID=
  OAUTH_GOOGLE_CLIENT_SECRET=
  OAUTH_MICROSOFT_CLIENT_ID=
  OAUTH_MICROSOFT_CLIENT_SECRET=
  OAUTH_MICROSOFT_TENANT=common
  OAUTH_APPLE_TEAM_ID=
  OAUTH_APPLE_KEY_ID=
  OAUTH_APPLE_PRIVATE_KEY_PATH=
  OAUTH_REDIRECT_URI_ADMIN=https://erp.example.com/api/admin/oauth/callback/
  OAUTH_REDIRECT_URI_PORTALE=https://erp.example.com/api/portale/oauth/callback/
  OAUTH_REDIRECT_URI_SHOP=https://erp.example.com/api/shop/oauth/callback/
  ```
- **Console provider**: configurare redirect URI whitelist per ogni ambiente (dev/staging/prod). Setup: 1-2h per provider × 3 ambienti.
- **Redis**: riuso del Redis esistente (permessi cache) per salvare state OAuth con TTL.

---

# C. Stima sprint e ordine consigliato

| Fase                                                             | Sprint | Complessità   |
| ---------------------------------------------------------------- | :----: | ------------- |
| **A. 2FA TOTP completo** (DB già fatto, resta BE+FE+test)         |  1–2   | Media         |
| **B.1 MVP OAuth — Google su canale ADMIN**                        |   1    | Bassa-Media   |
| **B.2 Estensione OAuth — Microsoft + canale PORTALE**             |   1    | Bassa         |
| **B.3 Linking + unlink UI + OTP conferma**                        |  ~1    | Media         |
| **B.4 Shop B2C self-signup + Apple Sign-In**                      |   1    | Media         |
| **B.5 Hardening — refresh validation, revocation list, WebAuthn** |   2+   | Alta          |
| **Totale copertura completa 2FA + OAuth multi-canale**            | **4–5**| —             |

**Ordine consigliato**: A prima di B. Motivazione: 2FA è già per metà pronto (DB), chiude un debito architetturale, e il middleware `TotpRequiredMiddleware` va integrato prima dell'OAuth per evitare di riscriverlo due volte (OAuth post-2FA è semplice se il middleware esiste già).

---

# D. Brief DB complessivo (da passare al team DB)

## D.1 Per 2FA (Parte A)

- [ ] **D.1.a** — Aggiornare `script.fn_get_user_profile()`: aggiungere `totp_abilitato` e `totp_obbligatorio` nel JSONB, **leggendo `totp_obbligatorio` da `identita_digitali`** per l'identità corrente (non da `risorse_umane_auth_user`). Cfr. `fn_get_user_profile_auth_flags.md` esistente come template.
- [ ] **D.1.b** *(opzionale)* — Trigger `trgfn_risorse_umane_auth_user_sync_totp_obbligatorio` per tenere in sync il flag legacy con `identita_digitali` (veste OPERATORE).

## D.2 Per OAuth (Parte B)

- [ ] **D.2.a** — Nuova tabella `config.identita_provider_mapping` (schema in §B.2.1) con UNIQUE `(provider, provider_sub)`, FK verso `identita_digitali` con ON DELETE CASCADE.
- [ ] **D.2.b** — ALTER TABLE `identita_digitali` ADD COLUMN `login_methods TEXT[] NOT NULL DEFAULT ARRAY['PASSWORD']`.
- [ ] **D.2.c** — Trigger `trgfn_identita_provider_mapping_sync_methods` (§B.2.2) per sync `login_methods` ↔ mapping attivi.
- [ ] **D.2.d** — Trigger `trgfn_identita_digitali_guard_login_methods` (§B.2.3) per evitare identità senza metodo di login.
- [ ] **D.2.e** — Seed codici errore OAuth in `config.messaggi_errore` (lingue IT + EN, §B.3.7).
- [ ] **D.2.f** *(storicizzazione)* — Tabella `storico_identita_provider_mapping` coerente con il pattern `storicizza=true` di altre tabelle config.

Tutti i changeset vanno in `db/changelog/migrations_v2/` con numerazione progressiva e `logicalFilePath`, secondo convenzioni AGENTS.md §"Liquibase v2 Workflow".

---

# E. Note di coesistenza 2FA + OAuth

- **2FA si applica a persone fisiche** (auth_user), OAuth è un metodo di autenticazione dell'identità digitale. Flow composto: login OAuth → identità trovata → se `totp_obbligatorio && device_attivo` → chiedere codice TOTP → JWT finale.
- Se un utente ha sia password che Google linkato: disabilitando una, l'altra resta utilizzabile. Il guard `trgfn_identita_digitali_guard_login_methods` impedisce di rimuoverle tutte.
- Recovery codes 2FA funzionano anche dopo OAuth (sono legati all'auth_user, non al metodo di login).
- **Non** implementare policy "se hai OAuth sei esente da 2FA": alcuni provider non fanno MFA, lasciare la scelta al security officer via `totp_obbligatorio` per-identità.

---

*2FA + Provider esterni (OAuth) — WIP ZeroERP. Rinominato e aggiornato 2026-04-23. Backend agent.*
