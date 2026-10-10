# Autenticazione — 2FA TOTP e provider esterni (OAuth) — chiuso (Parte A); Parte B nel suo piano

> Documento di pianificazione per l'estensione del sistema di autenticazione.
>
> **Data creazione originale**: 2026-04-01 (solo 2FA TOTP)
> **Aggiornato**: 2026-04-23 — aggiunto piano OAuth/SSO
> **Riscritto**: 2026-09-25 — riallineato al modello **credenziale + vesti**
> ([brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md),
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
>   [brief sicurezza](brief-be-fe-sicurezza-header-token-mfa.md) §3 (decisioni
>   di Tid del 2026-09-26/28). **DB chiuso il 2026-09-29**
>   ([brief-db-secondo-fattore-totp.md](brief-db-secondo-fattore-totp.md):
>   obbligo sulla credenziale o sul profilo, sei verbi del device, anti-replay
>   sul passo); **BE/FE in corso dal 2026-09-30** coi lotti T-0 → T-5 del brief
>   sicurezza §3.4-bis. ⚠️ La sede del lavoro sono quei due brief: la Parte A
>   di questo documento resta come **disegno d'origine**, e dove dissente vale
>   il brief.
> * **Parte B (provider esterni / OAuth): spostata il 2026-10-02** nel piano
>   [piano-autenticazione-provider-esterni-oauth.md](../work-in-progress/piano-autenticazione-provider-esterni-oauth.md)
>   (pianificata, non in sviluppo), con le sue righe di §C e §D, §E e le domande
>   aperte di §F. Qui resta il rimando.
>
> ✅ **Documento CHIUSO e archiviato il 2026-10-02** (decisione di Tid): la Parte A
> è costruita; la Parte B vive nel suo piano.
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
[piano-be-fe-accessi-credenziale-e-vesti.md](../work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md)).

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

➡️ **Spostata il 2026-10-02** in [piano-autenticazione-provider-esterni-oauth.md](../work-in-progress/piano-autenticazione-provider-esterni-oauth.md):
schema DB, backend, frontend, sicurezza, test e infrastruttura. Il testo non si ricopia qui:
due copie dello stesso piano divergerebbero.

---

# C. Stima e ordine consigliato

La Parte A è costruita (2026-09-29 → 10-02). La stima e l'ordine delle fasi OAuth stanno nel
[piano OAuth](../work-in-progress/piano-autenticazione-provider-esterni-oauth.md) §C.

---

# D. Brief DB complessivo (da passare al team DB, dopo §F)

## D.1 Per il 2FA (parte A)

✅ Tutto chiuso dal [brief DB del secondo fattore](brief-db-secondo-fattore-totp.md)
(2026-09-29): sede dell'obbligo (credenziale + profilo), i verbi `script.fn_totp_*`, il profilo,
il manuale di `config.auth_totp_device`, il TOTP nel freno. Le caselle qui sotto sono quelle di
partenza.

* [ ] **D.1.a** — La sede dell'obbligo, secondo Q-1.
* [ ] **D.1.b** — Le funzioni di `script` sul dispositivo TOTP (A.1.2.b), con
  il confine deciso in Q-6.
* [ ] **D.1.c** — `fn_get_user_profile`: `totp_abilitato` e `totp_obbligatorio`
  (A.1.2.c), con il default dell'assenza in una sola funzione.
* [ ] **D.1.d** — Riscrittura del manual di `config.auth_totp_device`: togliere
  la sezione su `risorse_umane_auth_user`, collegarlo a `config.credenziali`.
* [ ] **D.1.e** — Il TOTP nel freno, se Q-2 lo decide.

## D.2 Per OAuth (parte B)

➡️ Nel [piano OAuth](../work-in-progress/piano-autenticazione-provider-esterni-oauth.md) §D.

---

# E. 2FA e OAuth insieme

➡️ Nel [piano OAuth](../work-in-progress/piano-autenticazione-provider-esterni-oauth.md) §E.

---

# F. Domande aperte (da decidere con Tid prima dello sviluppo)

> ➡️ Le domande ancora aperte (Q-4, Q-5, Q-7, Q-8, Q-9, e la Q-10 da confermare) sono state
> spostate nel [piano OAuth](../work-in-progress/piano-autenticazione-provider-esterni-oauth.md) §F
> il 2026-10-02: la tabella qui sotto è quella di partenza, tenuta come storia.

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

*2FA + provider esterni (OAuth) — ZeroERP, archiviato il 2026-10-02. Riscritto il 2026-09-25 sul
modello credenziale + vesti. Backend agent.*
