# Autenticazione — 2FA TOTP e provider esterni (OAuth) — WIP

> Documento di pianificazione per l'estensione del sistema di autenticazione.
>
> **Data creazione originale**: 2026-04-01 (solo 2FA TOTP)
> **Aggiornato**: 2026-04-23 — aggiunto piano OAuth/SSO
> **Riscritto**: 2026-09-25 — riallineato al modello **credenziale + vesti**
> ([brief-db-blocco-login-per-credenziale.md](../work-done/brief-db-blocco-login-per-credenziale.md),
> P-1 e P-2 applicati il 2026-09-25). La versione di aprile metteva l'obbligo
> del 2FA sulla veste (`identita_digitali.totp_obbligatorio`) e citava
> `risorse_umane_auth_user`: entrambe le cose non esistono più.
> **Stato**:
>
> * **Parte A (TOTP): ✅ COSTRUITA il 2026-10-02** (DB 29-09, BE/FE T-0 → T-4,
>   collaudo di Tid lo stesso giorno). Stato attuale nella guida
>   `guide/risorse-umane-e-accessi.md` («Secondo fattore di autenticazione») e
>   nel manuale `backend/core/manual/api_secondo_fattore.md`. Storia: Il rinvio di D-10 (2026-09-24: *«funzione
>   nuova, non un difetto, non si costruisce ora»*) è superato dal
>   [brief sicurezza](../work-done/brief-be-fe-sicurezza-header-token-mfa.md) §3 (decisioni
>   di Tid del 2026-09-26/28). **DB chiuso il 2026-09-29**
>   ([brief-db-secondo-fattore-totp.md](../work-done/brief-db-secondo-fattore-totp.md):
>   obbligo sulla credenziale o sul profilo, sei verbi del device, anti-replay
>   sul passo); **BE/FE in corso dal 2026-09-30** coi lotti T-0 → T-5 del brief
>   sicurezza §3.4-bis. ⚠️ La sede del lavoro sono quei due brief: la Parte A
>   di questo documento resta come **disegno d'origine**, e dove dissente vale
>   il brief.
> * **Parte B (provider esterni / OAuth): PIANIFICATO — non in sviluppo.** Prima
>   di partire vanno chiuse le **domande aperte del §F**.
>
> Copertura:
>
> * **Parte A**: 2FA TOTP (Google Authenticator, Authy, …)
> * **Parte B**: autenticazione tramite provider esterni (Google, Microsoft, Apple, …)
>
> Entrambe estendono lo stesso flusso di login e toccano la stessa sede, la
> **credenziale**: si trattano insieme per evitare due disegni divergenti.

---

## 0. Premessa — com'è l'autenticazione oggi (verificato 2026-09-25)

### 0.1 Una persona, una credenziale, più vesti

* **`django.auth_user`** = la **credenziale**: nome utente, email, password.
  **Una persona, una credenziale** (D-6): la password è una sola e vale per
  tutte le porte.
* **`config.credenziali`** (1:1 con `auth_user`) = lo **stato della
  credenziale**: `deve_cambiare_password`, `fallimenti_consecutivi`,
  `ultimo_fallimento_at`, blocco dell'amministratore (`bloccata_at`,
  `bloccata_da`, `motivo_blocco`). La riga nasce alla prima scrittura; la sua
  **assenza** vale «nessun errore, non bloccata, nessun obbligo». Nessuno la
  legge o la scrive fuori dal DB: lo fanno le funzioni di `script`. Niente
  storico, niente RLS ([manual](../../dbzero/config/tabelle/credenziali)).
* **`config.credenziali_provenienze`** = il **freno** sulla coppia
  *credenziale + provenienza* (IP fidato del chiamante): le password sbagliate
  frenano **chi le prova**, non il titolare
  ([manual](../../dbzero/config/tabelle/credenziali_provenienze)).
* **`anagrafiche.identita_digitali`** = le **vesti**: una riga per ogni ruolo
  applicativo attivo della persona (UNIQUE `(auth_user_id, ruolo_applicativo)
  WHERE attivo`). Porta solo ciò che è della veste: `attivo`, validità,
  `invito_inviato_at`. Dal 2026-09-25 (`20260925-25`) **non** porta più
  tentativi, blocco, cambio password né `totp_obbligatorio`
  ([manual](../../dbzero/anagrafiche/tabelle/identita_digitali)).
* Ruoli applicativi: `OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`,
  `SHOP_CUSTOMER`, `API_CLIENT`, `DISABILITATO`.
* `risorse_umane_auth_user` **non esiste più** (vista di compatibilità
  ritirata; model Django rimosso il 2026-09-12). Il legame con la risorsa umana
  passa da `identita_digitali.soggetto_ruolo_id`.

⭐ **Conseguenza per questo piano.** Il secondo fattore protegge la
**password**, e la password è una: il dispositivo TOTP e (secondo D-10)
l'obbligo di usarlo appartengono alla **credenziale**, non alla veste. Resta
aperto se una **porta** possa chiedere il TOTP *in più* (§F, Q-1).

### 0.2 Login oggi (tre porte)

* `POST /api/v1/admin/token/` → `OPERATORE`, `API_CLIENT`
* `POST /api/v1/portale/token/` → `CLIENTE_PORTALE`, `FORNITORE_PORTALE`
* `POST /api/v1/shop/token/` → `SHOP_CUSTOMER`

Portale e shop entrano con l'**email**, l'operatore con il nome utente (D-9,
lotto L-4 di
[piano-be-fe-accessi-credenziale-e-vesti.md](piano-be-fe-accessi-credenziale-e-vesti.md)).

La sequenza, in `AuditTokenObtainPairView.post`
([auth_views.py](../../../../backend/apps/core/api/auth_views.py)):

1. **provenienza** (IP fidato, `get_client_ip`); se manca, rifiuto
   `E_AUTH_CHIAMATA_NON_VALIDA` (fail-closed, prima di cercare l'utente);
2. `script.fn_check_blocco_login(auth_user_id, provenienza)`: blocco
   dell'admin (`E_CREDENZIALE_BLOCCATA`), freno sulla provenienza
   (`E_UTENTE_BLOCCATO`), attesa crescente (`E_LOGIN_ATTESA`);
3. verifica della password (SimpleJWT) tramite il serializer della porta,
   sottoclasse di `MultiVesteTokenSerializer`
   ([multi_veste_token_serializer.py](../../../../backend/apps/core/api/multi_veste_token_serializer.py)),
   che risolve la veste e mette nel JWT `identita_id`, `ruolo_applicativo` e `sid`;
4. `script.fn_registra_tentativo_login(...)`: conta il fallimento, oppure
   azzera la provenienza dopo un successo.

Poi `set_jwt_gucs()` porta l'identità nelle GUC `app.*` a ogni richiesta
([jwt_audit_authentication.py](../../../../backend/apps/core/api/jwt_audit_authentication.py)).
Il cambio password obbligatorio lo fa rispettare `PasswordChangeRequiredMiddleware`;
dal punto di vista del JWT è ancora da sistemare (lotto L-6 del piano accessi).

### 0.3 Cosa ancora NON c'è

* **2FA TOTP**: esiste solo la tabella `config.auth_totp_device`. Nessuna
  dipendenza Python (`pyotp`, `qrcode`), nessun servizio, endpoint, middleware
  o schermata. Nessuna colonna di obbligo.
* **Provider esterni (OAuth/OIDC)**: niente di niente (né dipendenze, né
  tabelle, né endpoint).
* Fuori scope: magic link senza password, WebAuthn/Passkey (possibile
  evoluzione, §C).

---

# Parte A — 2FA TOTP

## A.1 DB

### A.1.1 `config.auth_totp_device` — ESISTE ✅

Stato effettivo ([doc tabella](../../dbzero/config/tabelle/auth_totp_device)):

```text
config.auth_totp_device
├── id                  BIGINT PK
├── auth_user_id        INTEGER NOT NULL, UNIQUE, FK → django.auth_user
│                       (1:1 con la credenziale: un solo dispositivo per persona)
├── secret_encrypted    VARCHAR NOT NULL   (Fernet, chiave da SECRET_KEY:
│                                           apps/core/services/crypto_service.py)
├── abilitato           BOOLEAN NOT NULL DEFAULT false
├── confermato          BOOLEAN NOT NULL DEFAULT false   (true dopo la prima verifica)
├── recovery_codes_hash JSONB NOT NULL DEFAULT '[]'      (hash SHA-256, monouso)
├── ultimo_codice_usato VARCHAR NULL                     (anti-replay)
├── ultimo_uso_at       TIMESTAMPTZ NULL
├── meta                JSONB NOT NULL DEFAULT '{}'
└── audit (data_insert, user_insert, data_update, user_update)
```

La FK verso `django.auth_user` sta in `90_end`
(`20260921-02-fk-config-auth-totp-device-auth-user-id-django-auth-user`),
nella forma di casa per le FK verso Django. È lo stesso schema e la stessa
forma di `config.credenziali`: le due tabelle sono **sorelle**, entrambe 1:1
con la credenziale.

⚠️ **Il manual della tabella è superato**
([manual/auth_totp_device.md](../../dbzero/config/manual/auth_totp_device.md)):
la sezione «Collegamento con risorse_umane_auth_user» parla di
`totp_obbligatorio` su una tabella che non esiste più. Va riscritta dal team
DB (§D.1.d).

### A.1.2 Da fare — DB

* [ ] **A.1.2.a — La sede dell'obbligo.** ❓ Dipende da **Q-1** (§F).
  Qualunque sia la risposta, l'obbligo **non** torna su `identita_digitali`.
  Le forme possibili sono descritte in Q-1.
* [ ] **A.1.2.b — Le funzioni del TOTP in `script`.** Come per
  `config.credenziali`, il backend non dovrebbe scrivere a mano la tabella del
  dispositivo. Servono funzioni che, dentro il DB, facciano: registrazione del
  dispositivo non confermato, conferma, disattivazione, consumo di un codice di
  recupero, aggiornamento dell'anti-replay. La **verifica crittografica** del
  codice resta al backend (`pyotp`), perché il segreto si decifra con la chiave
  applicativa. ❓ Il confine preciso (chi legge il segreto cifrato, e come) è
  **Q-6**.
* [ ] **A.1.2.c — Il profilo utente.** `script.fn_get_user_profile()` espone
  già `deve_cambiare_password`, letto dalla credenziale tramite
  `fn_get_deve_cambiare_password`. Va esteso con:
  * `totp_abilitato`: EXISTS su `auth_totp_device` con `abilitato AND confermato`;
  * `totp_obbligatorio`: dalla sede decisa in Q-1.

  Il valore di default dell'assenza deve stare in **una sola funzione**, come
  per `deve_cambiare_password`.
* [ ] **A.1.2.d — Il TOTP e il freno.** ❓ Dipende da **Q-2**: se i codici TOTP
  sbagliati contano, `fn_registra_tentativo_login` (o una funzione sorella)
  deve riceverli.

## A.2 Backend

### A.2.1 `TotpService` — `apps/core/services/totp_service.py`

* [ ] **A.2.1** — Servizio con queste responsabilità (le scritture passano
  dalle funzioni DB di A.1.2.b):
  * `setup_device(auth_user_id) → {secret, provisioning_uri, qr_code_base64, recovery_codes}`
    * segreto con `pyotp.random_base32()`, cifrato con `crypto_service` (Fernet);
    * 10 codici di recupero, salvati solo come hash SHA-256;
    * codici in chiaro restituiti **una sola volta**.
  * `confirm_setup(auth_user_id, codice) → bool`
    * `pyotp.TOTP(secret).verify(codice, valid_window=1)`; se valido,
      `confermato = abilitato = true`.
  * `verify(auth_user_id, codice) → {valido, tipo, recovery_rimanenti}`
    * anti-replay su `ultimo_codice_usato`;
    * prima il TOTP, poi i codici di recupero (monouso: l'hash esce dall'array).
  * `disable(auth_user_id)`: `abilitato=false`, segreto e codici azzerati.
  * `regenerate_recovery_codes(auth_user_id, codice_totp)`: richiede un codice
    TOTP valido.

### A.2.2 Login in due passi

* [ ] **A.2.2 — Passo 1**, sulle tre porte (`/api/v1/{admin,portale,shop}/token/`).
  La sequenza del §0.2 resta **uguale fino al passo 3 compreso** (provenienza,
  blocco e freno, password). Dopo una password corretta e **prima** di emettere
  il JWT:
  * se la credenziale ha un dispositivo attivo **oppure** l'obbligo vale per
    questa credenziale/porta (Q-1):
    * **non** si emette il JWT;
    * si risponde `{ two_factor_required: true, two_factor_token: "<token>" }`;
    * `two_factor_token` è firmato (`TimestampSigner`, scadenza 5 minuti) e
      porta `{auth_user_id, identita_id, porta, provenienza}`. La veste è già
      risolta: il passo 2 non la risolve di nuovo;
  * altrimenti, flusso JWT normale.
  * ❓ Se la password è giusta ma serve il TOTP, il successo sulla provenienza
    (l'azzeramento del freno) si registra **subito** o solo **dopo** il TOTP?
    Vedi Q-2.
* [ ] **A.2.3 — Passo 2**: `POST /api/v1/{porta}/token/2fa-verify/`
  * input `{ two_factor_token, code }`;
  * controllo di firma e scadenza, e che la **provenienza** coincida con quella
    del passo 1;
  * si ricontrolla `fn_check_blocco_login`: un blocco dell'admin arrivato fra i
    due passi deve valere;
  * `TotpService.verify(...)`; se è valido si emette il JWT con l'`identita_id`
    del token;
  * se è stato usato un codice di recupero, la risposta porta «ti restano N codici».

### A.2.3 Endpoint self-service

Nello stesso spazio di `api/v1/auth/change-password/`:

* [ ] **A.2.4** — `POST /api/v1/auth/2fa/setup/`: QR, segreto base32 e codici
  di recupero (una volta sola).
* [ ] **A.2.5** — `POST /api/v1/auth/2fa/confirm/`: primo codice valido.
* [ ] **A.2.6** — `POST /api/v1/auth/2fa/disable/`: chiede la password
  corrente; è rifiutato se l'obbligo vale per la credenziale (Q-1).
* [ ] **A.2.7** — `POST /api/v1/auth/2fa/recovery-codes/`: chiede un codice
  TOTP valido.

### A.2.4 Verbi dell'amministratore

* [ ] **A.2.8** — Disattivazione d'emergenza del dispositivo (telefono perso).
* [ ] **A.2.9** — Impostare o togliere l'obbligo (se Q-1 lo mette sulla
  credenziale).
* [ ] **A.2.10** — Traccia di ogni verbo, con autore e motivo.

❓ **Chi** può usare questi verbi (solo SUPER_ADMIN, come il blocco della
credenziale per D-B1, oppure un permesso d'area), **dove** stanno (vicino ai
verbi di blocco e sblocco di `amm_software`, lotto L-2) e se disattivare il
dispositivo chiude le sessioni aperte: **Q-3**.

### A.2.5 Middleware «2FA obbligatorio non configurato»

* [ ] **A.2.11** — `TotpRequiredMiddleware`, dopo `JwtAuditMiddleware` e prima
  di `PasswordChangeRequiredMiddleware`. Se l'obbligo vale e il dispositivo non
  è attivo:
  * lascia passare solo `/auth/2fa/setup/`, `/auth/2fa/confirm/`, il logout e
    il profilo;
  * tutto il resto riceve 403 `E_2FA_SETUP_RICHIESTO`.
  * ⚠️ Deve leggere l'obbligo in modo compatibile con il JWT: è lo stesso
    problema del cambio password obbligatorio (A-8, lotto L-6 del piano
    accessi), da risolvere **con lo stesso meccanismo** e non con un secondo.

### A.2.6 Codici errore

* [ ] **A.2.12** — Codici nuovi in `codici_errore.csv`, per esempio
  `E_2FA_SETUP_RICHIESTO`, `E_2FA_CODICE_NON_VALIDO`, `E_2FA_TOKEN_SCADUTO`,
  `E_2FA_OBBLIGATORIO_NON_DISATTIVABILE`. Poi si rigenerano
  `error_policies_generated.py` **e** il ripiego `error_messages_fallback.py`.

## A.3 Frontend

* [ ] **A.3.1** — `LoginView.vue` (una vista per tutte le porte): se la
  risposta porta `two_factor_required`, compare l'inserimento del codice a 6
  cifre con il link «Usa un codice di recupero», e si chiama `/token/2fa-verify/`.
* [ ] **A.3.2** — Sezione «Sicurezza» nel profilo: stato (abilitato /
  disabilitato / obbligatorio da configurare), procedura guidata (QR + segreto
  testuale → codice di conferma → codici di recupero con download `.txt` e
  stampa → «ho salvato i codici»), pulsanti «Disabilita» e «Rigenera i codici».
* [ ] **A.3.3** — Pannello operatore (admin): stato del 2FA **della
  credenziale** e i verbi di A.2.8–A.2.9 con `useConfirmAction`. Per chi ha
  anche vesti portale o shop, dev'essere chiaro che il 2FA vale per la persona
  e non per la sola veste.
* [ ] **A.3.4** — Guard di rotta: se l'obbligo vale e il TOTP non è abilitato,
  si va alla configurazione (stesso schema del cambio password obbligatorio).

## A.4 Test

* [ ] **A.T.1** — `setup_device()`: segreto, QR e codici di recupero.
* [ ] **A.T.2** — `confirm_setup()` con un codice valido.
* [ ] **A.T.3** — Login in due passi completo, sulle **tre** porte, con
  chiamata **reale** (non mock) al DB, come `test_login_credenziale_db`.
* [ ] **A.T.4** — Anti-replay: lo stesso codice due volte di fila viene rifiutato.
* [ ] **A.T.5** — Codice di recupero: consumato, contatore che scende.
* [ ] **A.T.6** — Verbo dell'admin: disattivazione, con la traccia.
* [ ] **A.T.7** — Il middleware blocca quando l'obbligo vale e il dispositivo manca.
* [ ] **A.T.8** — Stessa persona con vesti OPERATORE e CLIENTE_PORTALE: il
  dispositivo è uno solo e vale su entrambe le porte. L'eventuale richiesta in
  più di una porta dipende da Q-1.
* [ ] **A.T.9** — Codici TOTP sbagliati e freno (Q-2).
* [ ] **A.T.10** — Blocco dell'admin arrivato fra passo 1 e passo 2: il passo
  2 viene rifiutato.

## A.5 Dipendenze Python

| Pacchetto | Versione | Scopo                                    |
| --------- | -------- | ---------------------------------------- |
| `pyotp`   | >= 2.9   | Generazione e verifica dei codici TOTP   |
| `qrcode`  | >= 8.0   | QR code per configurare l'app            |
| `Pillow`  | >= 11.0  | Immagine del QR (dipendenza di `qrcode`) |

Vanno in `backend/requirements.in`, poi si rigenera `requirements.txt` con
`pip-compile`. ⛔ Sono **dipendenze nuove**: serve l'ok esplicito di Tid.

---

# Parte B — Autenticazione tramite provider esterni (OAuth/OIDC)

## B.1 Obiettivo e scope

Entrare da una o più porte (admin, portale, shop) con un provider OAuth/OIDC
esterno: **Google**, **Microsoft**, **Apple**, estendibile (GitHub, LinkedIn,
IdP aziendali come Okta o un tenant Azure AD).

**Invariante**: il login esterno produce **lo stesso JWT interno** del login
con password (`identita_id`, `ruolo_applicativo`, `sid`). Permessi, GUC e guard
di rotta **non cambiano**.

⭐ **Cosa cambia col modello a credenziale.** Il provider autentica la
**persona**, cioè fa lo stesso lavoro della password: sostituisce la *prova di
possesso della credenziale*, non la scelta della veste, che resta della porta
come oggi. Da qui la domanda di fondo della parte B: il collegamento col
provider sta sulla **credenziale** o sulla **veste**? È **Q-4**. Lo schema qui
sotto è scritto nella forma «sulla credenziale», coerente con D-6 e D-10, ma
**non è deciso**.

## B.2 Schema DB proposto (da confermare dopo Q-4)

### B.2.1 Tabella del collegamento col provider

* [ ] **B.2.1** — Brief al team DB. Forma «sulla credenziale»:

```sql
CREATE TABLE config.credenziali_provider (
    id               BIGSERIAL PRIMARY KEY,
    auth_user_id     INTEGER NOT NULL,        -- FK → django.auth_user in 90_end (forma di casa)
    provider         VARCHAR(50)  NOT NULL,   -- 'google', 'microsoft', 'apple'
    provider_sub     VARCHAR(500) NOT NULL,   -- subject dell'IdP, stabile per provider
    provider_email   VARCHAR(254),            -- email al momento del collegamento (audit/UI)
    provider_name    VARCHAR(255),            -- nome visualizzato (audit/UI)
    attivo           BOOLEAN NOT NULL DEFAULT true,
    linked_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_login_at  TIMESTAMPTZ,
    meta             JSONB NOT NULL DEFAULT '{}',
    -- audit standard; storicizzazione: vedi sotto
);

-- Un subject di un provider appartiene a una sola credenziale
ALTER TABLE config.credenziali_provider
  ADD CONSTRAINT uq_credenziali_provider_provider_sub UNIQUE (provider, provider_sub);
```

Nella forma alternativa «sulla veste», la FK punterebbe a
`identita_digitali.id`: la stessa persona dovrebbe collegare Google una volta
per porta.

**Perché così**:

* **UNIQUE `(provider, provider_sub)`**: un account Google porta a una sola
  credenziale; evita il collegamento ombra.
* **FK verso `django.auth_user` in `90_end`**, con `preCondition tableExists` e
  `MARK_RAN`, come `auth_totp_device` e `credenziali`: in CI la FK non c'è.
* **Storico**: a differenza di `credenziali` (che cambia a ogni password
  sbagliata), collegare e scollegare è un atto raro e da tracciare. ❓ Serve lo
  storico sulla riga oppure un registro di eventi? Lo decide il team DB, e
  `ultimo_login_at` non deve generare uno snapshot a ogni accesso.

### B.2.2 I metodi di accesso della credenziale

La versione di aprile aggiungeva `identita_digitali.login_methods TEXT[]`,
tenuto allineato da un trigger. Nel modello attuale i metodi sono della
**credenziale**, e un array derivato da un'altra tabella è una copia che può
divergere.

* [ ] **B.2.2** — ❓ **Q-5**: servono un campo derivato, o bastano la presenza
  di una password utilizzabile più le righe attive di `credenziali_provider`,
  letti da una funzione? Questa pagina propone la **funzione** (nessuna copia),
  ma la decisione è aperta.

### B.2.3 Guard: la credenziale non resta senza modo di entrare

* [ ] **B.2.3** — Brief DB: un guard che rifiuti lo scollegamento dell'ultimo
  provider quando la credenziale non ha una password utilizzabile. Errore
  `E_CREDENZIALE_SENZA_METODO_LOGIN`. Il guard va sulla **credenziale** (è lei
  che resta chiusa fuori), non sulla veste.

## B.3 Backend

### B.3.1 Dipendenze

* [ ] **B.3.1** — Da aggiungere a `backend/requirements.in` (⛔ ok esplicito di Tid):

| Pacchetto                        | Versione | Scopo                              |
| -------------------------------- | -------- | ---------------------------------- |
| `django-allauth[socialaccount]`  | >= 0.57  | Framework OAuth multi-provider     |
| `requests-oauthlib`              | >= 1.3   | Client OAuth per i flussi custom   |

`django-allauth` è preferito a `social-auth-app-django`: è mantenuto, supporta
PKCE nativamente, ha hook espliciti (`pre_social_login`) per agganciarsi alla
nostra risoluzione di credenziale e veste, e supporta OIDC discovery.

### B.3.2 Configurazione

* [ ] **B.3.2** — `settings.py`: `INSTALLED_APPS` (`allauth`,
  `allauth.account`, `allauth.socialaccount` + provider),
  `SOCIALACCOUNT_PROVIDERS` con client id e secret da variabili d'ambiente
  (`OAUTH_PKCE_ENABLED: True`), `SOCIALACCOUNT_ADAPTER =
  'apps.core.api.oauth_adapter.ZeroErpSocialAdapter'`,
  `SOCIALACCOUNT_AUTO_SIGNUP = False`. I segreti stanno in `.env` in sviluppo e
  in un secret manager in produzione; **mai** committati.

### B.3.3 Adapter: dal provider alla credenziale, poi alla veste

* [ ] **B.3.3** — `apps/core/api/oauth_adapter.py`, `pre_social_login`:
  1. ricava la porta dal path;
  2. cerca `(provider, sub)` in `credenziali_provider`;
  3. se lo trova ed è attivo, controlla il **blocco dell'admin** sulla
     credenziale (`fn_check_blocco_login`: il blocco vale da **ogni** porta e
     con **ogni** metodo, Q-7), poi risolve la veste della porta con la stessa
     logica di `MultiVesteTokenSerializer` (senza veste attiva:
     `VesteNonAttivaError`, come oggi);
  4. se non lo trova:
     * porta **admin** → rifiuto `E_OAUTH_OPERATORE_NON_INVITATO` (gli
       operatori si invitano; il primo accesso OAuth collega la credenziale
       creata dall'invito);
     * porte **portale/shop** → ❓ nuova registrazione, oppure collegamento a
       una credenziale esistente per email? Con l'email unica (D-9) il rischio
       di presa di possesso è concreto (§B.5.2): **Q-8**;
  5. aggiorna `ultimo_login_at` ed emette il JWT (B.3.5).

| Porta del callback           | Veste                                   | Registrazione autonoma? |
| ---------------------------- | --------------------------------------- | ----------------------- |
| `/api/v1/admin/oauth/`       | `OPERATORE`                             | ❌ solo invito          |
| `/api/v1/portale/oauth/`     | `CLIENTE_PORTALE`, `FORNITORE_PORTALE`  | ❓ Q-8                  |
| `/api/v1/shop/oauth/`        | `SHOP_CUSTOMER`                         | ❓ Q-8                  |

### B.3.4 Endpoint OAuth per porta

* [ ] **B.3.4**:
  * `GET /api/v1/{porta}/oauth/<provider>/authorize/`: redirect al provider;
    `state` e PKCE generati lato server e salvati in Redis (TTL 10 minuti,
    chiave `oauth_state:<uuid>`);
  * `GET /api/v1/{porta}/oauth/<provider>/callback/`: scambio del code,
    risoluzione (B.3.3), JWT. Se serve il 2FA (Q-1, Q-9) risponde con il
    `two_factor_token` di §A.2.2;
  * `POST /api/v1/auth/oauth/<provider>/link/`: collegamento da un utente già
    entrato (§B.5.2);
  * `POST /api/v1/auth/oauth/<id>/unlink/`: scollegamento (dall'utente stesso
    o dall'admin), soggetto al guard di §B.2.3.

### B.3.5 Emissione del JWT dopo OAuth

* [ ] **B.3.5** — Un metodo di `MultiVesteTokenSerializer` (o un helper
  condiviso con il login a password) che emetta la coppia di token per una
  credenziale e una porta **senza** verificare la password. Resta **una sola**
  risoluzione della veste e **un solo** punto di emissione, con metadati di
  sessione `metodo_login = 'oauth_<provider>'`.

### B.3.6 Codici errore

* [ ] **B.3.6** — In `codici_errore.csv` (con la rigenerazione di policy e ripiego):
  `E_OAUTH_STATE_INVALIDO`, `E_OAUTH_CODE_SCAMBIO_FALLITO`,
  `E_OAUTH_PROVIDER_SUB_MANCANTE`, `E_OAUTH_EMAIL_NON_VERIFICATA`,
  `E_OAUTH_OPERATORE_NON_INVITATO`, `E_OAUTH_MAPPING_GIA_LINKATO`,
  `E_OAUTH_PROVIDER_DISABILITATO`, `E_CREDENZIALE_SENZA_METODO_LOGIN`.

## B.4 Frontend

* [ ] **B.4.1** — `LoginView.vue`: la sezione «Oppure accedi con» mostra i
  provider configurati **per quella porta** (`/api/v1/{porta}/oauth/providers/`).
  Il clic avvia un redirect vero del browser (non una chiamata XHR). Al ritorno
  il backend consegna il JWT al frontend. ❓ Come consegnarlo (frammento
  dell'URL o cookie di breve durata) è da decidere insieme al trasporto dei
  token di oggi.
* [ ] **B.4.2** — «Account collegati» nella sezione Sicurezza del profilo:
  elenco dei provider (provider, email, collegato il, ultimo accesso),
  «Collega…» e «Scollega», con avviso se lo scollegamento lascerebbe la
  credenziale senza modo di entrare.
* [ ] **B.4.3** — Pannello operatore (admin): i metodi di accesso **della
  credenziale** (password, provider, 2FA) e «Scollega provider» d'emergenza.

## B.5 Sicurezza — punti critici

### B.5.1 State CSRF e PKCE

`state` casuale di 32 byte URL-safe, in Redis con TTL 10 minuti, legato alla
sessione. PKCE su tutti i provider che lo supportano; con Apple è obbligatorio.

### B.5.2 Collegamento sicuro

**Lo scenario**: Mario ha la password su `mario@example.com`; qualcuno crea
`mario@example.com` presso un provider e prova a collegarlo. Collegare **per
email** significa consegnargli l'account. Con portale e shop che entrano per
email (D-9), l'email è una chiave: il rischio è maggiore, non minore.

**Decisione di aprile, confermata**: **mai** collegare automaticamente per
email. Il collegamento richiede sempre una di queste due cose:

* un utente già entrato con la password, più una conferma tramite OTP via email;
* per gli operatori, un collegamento preparato dall'admin al momento
  dell'invito.

### B.5.3 Revoca lato provider

Se il provider disabilita l'account, il JWT resta valido fino alla scadenza.
Si può ricontrollare presso il provider a ogni refresh (+1 chiamata), oppure
usare i webhook di revoca (fuori MVP). Il **blocco dell'admin** della
credenziale resta il modo immediato per chiudere, da ogni porta e con ogni
metodo.

### B.5.4 Email non verificata

Se il provider non dichiara `email_verified`, il login è rifiutato con
`E_OAUTH_EMAIL_NON_VERIFICATA`, su tutte le porte.

### B.5.5 GDPR (documentazione, non codice)

* [ ] **B.5.5** — Informativa privacy (quali dati del provider si conservano),
  DPA con i provider, prova del consenso (`linked_at` +
  `meta.consent_text_version`), diritto all'oblio (cancellazione del
  collegamento, e dello storico se c'è).

## B.6 Test

* [ ] **B.T.1** — Callback simulato: credenziale trovata, veste della porta
  risolta, JWT con i claim giusti.
* [ ] **B.T.2** — Porta admin senza invito → `E_OAUTH_OPERATORE_NON_INVITATO`.
* [ ] **B.T.3** — `state` scaduto → `E_OAUTH_STATE_INVALIDO`.
* [ ] **B.T.4** — Email non verificata → `E_OAUTH_EMAIL_NON_VERIFICATA`.
* [ ] **B.T.5** — Collegamento da utente entrato: OTP chiesto, verificato,
  collegamento creato.
* [ ] **B.T.6** — Scollegamento dell'ultimo metodo → `E_CREDENZIALE_SENZA_METODO_LOGIN`.
* [ ] **B.T.7** — 2FA dopo OAuth (Q-9): il callback emette il `two_factor_token`, non il JWT.
* [ ] **B.T.8** — Lo stesso `provider_sub` non si collega a due credenziali (UNIQUE).
* [ ] **B.T.9** — Credenziale bloccata dall'admin → il login OAuth è rifiutato.
* [ ] **B.T.10** — Credenziale collegata senza la veste della porta →
  `VesteNonAttivaError`, come con la password.

## B.7 Infrastruttura

* **Variabili d'ambiente**: `OAUTH_GOOGLE_CLIENT_ID/SECRET`,
  `OAUTH_MICROSOFT_CLIENT_ID/SECRET/TENANT`,
  `OAUTH_APPLE_TEAM_ID/KEY_ID/PRIVATE_KEY_PATH`,
  `OAUTH_REDIRECT_URI_{ADMIN,PORTALE,SHOP}`.
* **Console dei provider**: redirect URI in whitelist per ogni ambiente.
* **Redis**: quello che c'è (`django_redis`, `REDIS_URL`); in CI si usa
  `LocMemCache`, e per lo `state` basta.

---

# C. Stima e ordine consigliato

| Fase                                                          | Sprint | Complessità |
| ------------------------------------------------------------- | :----: | ----------- |
| **Prerequisito** — chiusura del piano accessi (L-2, L-4, L-6) |   —    | in corso    |
| **A. 2FA TOTP** (tabella pronta; restano obbligo, funzioni DB, BE, FE, test) |  1–2   | Media       |
| **B.1 MVP OAuth** — Google sulla porta admin                  |   1    | Bassa-Media |
| **B.2** — Microsoft + porta portale                           |   1    | Bassa       |
| **B.3** — Collega/scollega + conferma OTP                     |  ~1    | Media       |
| **B.4** — Shop con registrazione autonoma + Apple (se Q-8 la ammette) |   1    | Media       |
| **B.5** — Rafforzamento: validazione al refresh, revoca, WebAuthn |   2+   | Alta        |

**Ordine consigliato**: prima si chiude il piano accessi, poi A, poi B.

* Il piano accessi prima: il 2FA si innesta nella sequenza di login e nel
  meccanismo «obbligo compatibile col JWT» (L-6), che stanno cambiando adesso.
* A prima di B: il passo 2 del login e il middleware servono anche all'OAuth.

---

# D. Brief DB complessivo (da passare al team DB, dopo §F)

## D.1 Per il 2FA (parte A)

* [ ] **D.1.a** — La sede dell'obbligo, secondo Q-1.
* [ ] **D.1.b** — Le funzioni di `script` sul dispositivo TOTP (A.1.2.b), con
  il confine deciso in Q-6.
* [ ] **D.1.c** — `fn_get_user_profile`: `totp_abilitato` e `totp_obbligatorio`
  (A.1.2.c), con il default dell'assenza in una sola funzione.
* [ ] **D.1.d** — Riscrittura del manual di `config.auth_totp_device`: togliere
  la sezione su `risorse_umane_auth_user`, collegarlo a `config.credenziali`.
* [ ] **D.1.e** — Il TOTP nel freno, se Q-2 lo decide.

## D.2 Per OAuth (parte B)

* [ ] **D.2.a** — La tabella del collegamento col provider (§B.2.1), nella sede
  decisa da Q-4, con UNIQUE `(provider, provider_sub)` e FK in `90_end`.
* [ ] **D.2.b** — I metodi di accesso della credenziale (§B.2.2, Q-5).
* [ ] **D.2.c** — Il guard contro la credenziale senza metodo di accesso (§B.2.3).
* [ ] **D.2.d** — Storico o registro di eventi per collegamenti e scollegamenti.
* [ ] **D.2.e** — I codici errore (§B.3.6) in `codici_errore.csv`.

I changeSet seguono le convenzioni di
[linee-guida-sql.md](../../linee-guida-sql.md) e, per i guard,
[linee-guida-trigger.md](../../linee-guida-trigger.md).

---

# E. 2FA e OAuth insieme

* **Tutti e due sono della credenziale**: il 2FA protegge la persona, OAuth è
  un altro modo per dimostrare di essere lei. Il flusso composto è: OAuth →
  credenziale trovata → controllo del blocco → veste della porta → TOTP (se
  richiesto) → JWT.
* Chi ha password e Google collegato continua a entrare con l'una se l'altra
  viene tolta; il guard di §B.2.3 impedisce di toglierle tutte.
* I codici di recupero valgono qualunque sia il metodo di accesso.
* **Il blocco dell'admin vale per tutti i metodi e per tutte le porte.**

---

# F. Domande aperte (da decidere con Tid prima dello sviluppo)

> ✅ **Chiuse dalla Parte A (2026-09-28 → 10-02, brief sicurezza §6 e brief DB
> TOTP §7):** Q-1 → **tutte e due**, flag sulla credenziale **oppure** segno sul
> profilo (D-T1; il SUPER_ADMIN sempre); niente regola per porta. Q-2 → **sì**, il
> codice sbagliato conta nel freno della credenziale, e il successo si registra
> solo dopo il secondo passo (D-T2). Q-3 → solo **SUPER_ADMIN**, con motivo;
> disattivare **non** chiude le sessioni (decisione 8). Q-6 → **solo funzioni di
> `script`**, il backend verifica il codice e passa il passo. Q-10 → di fatto **il
> dispositivo resta** (il reset della password non lo tocca): da confermare se
> mai la si volesse diversa. Restano aperte quelle della Parte B.

| # | Domanda | Possibili risposte | Dove pesa |
| --- | --- | --- | --- |
| **Q-1** | **Dove sta l'obbligo del 2FA?** D-10 dice «sarà della credenziale» e lascia aperto «questa porta chiede il TOTP in più». | (a) una colonna su `config.credenziali` (una regola per tutte le porte); (b) una regola **per porta**, per esempio un parametro «la porta admin chiede il TOTP»; (c) tutte e due, con l'obbligo che vale se vale almeno una delle due | A.1.2.a, A.2.2, A.2.6, A.2.9, A.2.11, A.T.8, D.1.a |
| **Q-2** | **Un codice TOTP sbagliato conta come una password sbagliata?** Sei cifre si indovinano per forza bruta. E dopo una password giusta, il freno sulla provenienza si azzera subito o solo dopo il TOTP? | contare nel freno di `credenziali_provenienze`, oppure un contatore a parte; azzeramento dopo il passo 2 oppure dopo il passo 1 | A.1.2.d, A.2.2, A.T.9, D.1.e |
| **Q-3** | **Chi può usare i verbi 2FA dell'admin** (disattivare il dispositivo, imporre l'obbligo) e cosa fanno alle sessioni aperte? | solo SUPER_ADMIN come il blocco (D-B1), oppure un permesso d'area; blacklist delle sessioni sì o no | A.2.8–A.2.10, A.3.3 |
| **Q-4** | **Il collegamento col provider sta sulla credenziale o sulla veste?** | credenziale (un collegamento per persona, coerente con D-6 e D-10), oppure veste (un collegamento per porta) | B.2.1, B.3.3, D.2.a |
| **Q-5** | **I metodi di accesso sono un campo o una lettura?** | un campo derivato mantenuto da trigger, oppure una funzione che li calcola | B.2.2, D.2.b |
| **Q-6** | **Il confine DB/backend sul TOTP**: chi legge e scrive `auth_totp_device`? | solo funzioni di `script`, con il backend che verifica il codice e passa l'esito; oppure un repository backend con SQL diretto | A.1.2.b, A.2.1, D.1.b |
| **Q-7** | **Blocco dell'admin e OAuth**: la credenziale bloccata resta chiusa anche via provider? (Proposta: sì.) E il cambio password obbligatorio vale per chi entra solo via provider? | sì / no; per il cambio password: si ignora, oppure si chiede lo stesso | B.3.3, B.T.9 |
| **Q-8** | **Registrazione autonoma via provider su portale e shop**: si ammette? Se l'email esiste già come credenziale, cosa succede? | nessuna registrazione autonoma; oppure registrazione solo con email nuova; mai il collegamento automatico per email (§B.5.2) | B.3.3, B.4, §C fase B.4 |
| **Q-9** | **Il 2FA dopo OAuth**: richiesto sempre, oppure ci si fida dell'MFA dichiarato dal provider (claim `amr`)? | sempre (proposta di aprile, la più sicura); oppure fiducia verso una whitelist di provider | B.3.4, B.T.7 |
| **Q-10** | **Il reset della password tocca il 2FA?** Il reset dimostra solo il possesso dell'email; come il blocco dell'admin, il 2FA dovrebbe restare. | il dispositivo resta (proposta); oppure il reset lo disattiva | A.2.1, `password-reset-confirm` |

---

*2FA + provider esterni (OAuth) — WIP ZeroERP. Riscritto il 2026-09-25 sul
modello credenziale + vesti. Backend agent.*
