# Gestione Autenticazioni — WIP

> Documento di pianificazione per il completamento del sistema di autenticazione.
> Data inizio: 2026-03-28
> Stato: **FASI 1-3 COMPLETATE — Fase 4 (2FA) rimandata**
> Ultimo aggiornamento: 01-04-2026
>
> Dipende da:
>
> * Sistema JWT esistente (`AuditTokenObtainPairView`, `SidTokenObtainPairSerializer`)
> * Blocco login per tentativi falliti (`script.fn_check_blocco_login`)
> * Audit sessioni (`dbops.sessioni_utente`)
> * Reparti (`config.unita_organizzative`) e profili permessi
> * Bridge HR↔Auth (`anagrafiche.risorse_umane_auth_user`)
> * Contatti con email (`anagrafiche.contatti`)

---

## Motivazione

Il sistema di autenticazione attuale gestisce login JWT, blocco tentativi, permessi area/azioni
e audit sessioni. Mancano però funzionalità essenziali per un ERP in produzione:

1. **Notifiche email** — invito operatore, reset password, comunicazioni di sistema
2. **Cambio password obbligatorio** al primo accesso
3. **Reset password dimenticata** — self-service
4. **Autenticazione a due fattori (2FA)** — TOTP

Tutte le componenti devono essere **generiche e riutilizzabili**: il sistema email
deve supportare mittenti diversi per reparto/contesto, i token devono essere un
meccanismo unico riutilizzabile per qualsiasi flusso (invito, reset, conferma).

---

## Architettura dei building block riutilizzabili

Il piano si basa su **3 building block trasversali** che le fasi successive consumano:

```
┌─────────────────────────────────────────────────────────┐
│  BB-1  Sistema Email Generico (per reparto/contesto)    │
│        config.email_account + config.email_template     │
│        EmailDispatchService (Django)                    │
├─────────────────────────────────────────────────────────┤
│  BB-2  Token Monouso Generico                           │
│        config.token_monouso                             │
│        TokenService (Django)                            │
├─────────────────────────────────────────────────────────┤
│  BB-3  Flag Stato Credenziali                           │
│        anagrafiche.risorse_umane_auth_user              │
│        (deve_cambiare_password, 2fa_abilitato, ecc.)    │
└─────────────────────────────────────────────────────────┘
         ▲              ▲              ▲
         │              │              │
    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
    │ Fase 1  │   │ Fase 2  │   │ Fase 3  │
    │ Email + │   │ Reset   │   │ Invito  │
    │ Cambio  │   │ Password│   │ Primo   │
    │ Password│   │         │   │ Accesso │
    └─────────┘   └─────────┘   └─────────┘
                                     │
                               ┌─────┴─────┐
                               │  Fase 4   │
                               │  2FA TOTP │
                               └───────────┘
```

---

## Prerequisiti di sviluppo

### Infrastruttura — Strategia email a due fasi

**Fase sviluppo (attuale)**: backend console — le email vengono loggate nel
terminale Django e nel `config.email_log` senza invio SMTP reale.
Il `EmailDispatchService` rileva `settings.DEBUG = True` e account con
`smtp_host` vuoto → stampa in console + stato `SENT` nel log.
Zero dipendenze esterne, zero configurazione.

**Fase test reali (successiva)**: configurare un account SMTP reale.
Esempio con Gmail personale:

| Parametro | Valore |
| --- | --- |
| `smtp_host` | `smtp.gmail.com` |
| `smtp_port` | `587` |
| `smtp_use_tls` | `true` |
| `smtp_use_ssl` | `false` |
| `smtp_username` | `tuaemail@gmail.com` |
| `smtp_password_encrypted` | App Password 16 caratteri (generata da Google con 2FA attivo) |
| `email_from` | `ZeroErp Dev <tuaemail@gmail.com>` |

Procedura Gmail:

1. Abilitare 2FA sull'account Google
2. Generare App Password: myaccount.google.com → Sicurezza → Password per le app
3. Inserire la App Password come `smtp_password_encrypted` (verra' crittografata con Fernet)
4. Aggiornare il record `config.email_account` con codice `SISTEMA`

Limiti Gmail: 500 email/giorno, sufficiente per sviluppo e test.
Per produzione: valutare servizio dedicato (SendGrid, Mailgun, Amazon SES, SMTP aziendale).

**Prerequisiti (rimandati a fase test reali)**:

- [x] PRE-1 — Account SMTP configurato (Gmail App Password o servizio dedicato)
- [x] PRE-2 — Record `config.email_account` SISTEMA aggiornato con credenziali reali
- [x] PRE-3 — Test invio email end-to-end verificato

### DB esistente (già disponibile)

- [x] `config.unita_organizzative` — reparti con gerarchia parent_id
- [x] `anagrafiche.contatti` — email/PEC per soggetto, con `unita_organizzativa_id`
- [x] `anagrafiche.risorse_umane_auth_user` — bridge HR↔Django auth con `ruolo_sistema`
- [x] `script.fn_check_blocco_login` — blocco login per tentativi falliti
- [x] `script.fn_registra_tentativo_login` — registrazione tentativi
- [x] `config.profili_reparto_aree` / `config.profili_reparto_azioni` — permessi ereditati

### Backend esistente (già disponibile)

- [x] `AuditTokenObtainPairView` — login con audit e blocco
- [x] `ZeroERPPermission` — permission class con ruolo_sistema
- [x] `PermissionsResolver` — cache Redis L2 + L1
- [x] `session_audit_service` — logging LOGIN/REFRESH/LOGOUT
- [x] `sync_auth_user_active` — management command sincronizzazione scadenze
- [x] Password validators Django (4 validators configurati)

### Frontend esistente (già disponibile)

- [x] `LoginView.vue` — pagina login con gestione errori specifici
- [x] `auth.js` store — token management, refresh automatico
- [x] Route guard con check permessi area
- [x] Axios interceptor per 401 → refresh → retry

---

## Fase 1 — Building Block Email + Cambio Password Obbligatorio

> **Obiettivo**: creare il sistema email generico per reparto/contesto e il meccanismo
> di cambio password obbligatorio al primo accesso.
> Questa fase è il fondamento: le fasi successive la consumano.

### 1.1 BB-1: Sistema Email Generico

#### Concetto

Ogni reparto (unità organizzativa) può avere il proprio account email di uscita.
L'admin (ruolo_sistema = ADMIN) usa un account di sistema. Il sistema sceglie
automaticamente l'account mittente in base al contesto:

```
Richiesta invio email
  → contesto = "reparto_acquisti"
  → lookup: config.email_account WHERE unita_organizzativa_id = <id_acquisti>
  → trovato? → usa quello
  → non trovato? → fallback: account con codice_contesto = 'SISTEMA'
```

I template email sono parametrizzabili con variabili (`{{nome}}`, `{{link}}`, `{{azienda}}`).
Ogni template ha un `codice` univoco (es. `INVITO_OPERATORE`, `RESET_PASSWORD`).
I template possono essere sovrascritti per reparto e per tipo pratica.

#### Ambito di proprietà e visibilità

Ogni email (bozza e log) ha un **ambito** che determina chi può vederla:

```
┌──────────────────────────────────────────────────────────────────┐
│  Ambito         │ Significato              │ Visibilità          │
├──────────────────────────────────────────────────────────────────┤
│  SISTEMA        │ Email di infrastruttura   │ Solo ADMIN          │
│                 │ (inviti, reset, notifiche) │                     │
├──────────────────────────────────────────────────────────────────┤
│  REPARTO        │ Email del reparto          │ Tutti gli operatori │
│                 │ (comunicazioni a clienti/  │ dell'unità org.     │
│                 │  fornitori nel contesto    │ + ADMIN             │
│                 │  del reparto)              │                     │
├──────────────────────────────────────────────────────────────────┤
│  OPERATORE      │ Email personale            │ Solo l'operatore    │
│                 │ dell'operatore             │ che l'ha creata     │
│                 │                            │ + ADMIN             │
└──────────────────────────────────────────────────────────────────┘
```

Quando una email è legata a una **pratica** (`pratica_id`), è consultabile
anche dalla scheda pratica stessa — indipendentemente dall'ambito.
Questo permette di ricostruire la storia comunicativa di una pratica.

#### Risoluzione template: reparto + tipo pratica

I template possono essere specializzati non solo per reparto, ma anche per
**tipo pratica**. Questo permette testi diversi per la stessa azione in contesti diversi:

```
Azione "Invia comunicazione" dalla pratica
  → tipo_pratica = "RECLAMO", reparto = "Acquisti"
  → lookup: template con codice=COMUNICAZIONE_PRATICA
             + tipo_prestazione_id=<reclamo>
             + unita_organizzativa_id=<acquisti>
             + lingua='it'
  → non trovato? → fallback senza tipo_pratica
  → non trovato? → fallback sistema
```

Esempi:
- Reclamo (reparto Acquisti): "Gentile fornitore, in merito alla segnalazione..."
- Offerta (reparto Commerciale): "Gentile cliente, le confermiamo l'offerta..."
- Generico (sistema): "Comunicazione relativa alla pratica {{codice_pratica}}"

#### DB

- [x] 1.1.1 — Creare tabella `config.email_account` ✅ `20260328-13`

```
config.email_account
├── id                      SERIAL PK
├── codice                  VARCHAR(50) UNIQUE NOT NULL
├── descrizione             TEXT NOT NULL
├── unita_organizzativa_id  INTEGER NULL FK → config.unita_organizzative(id)
│                           (NULL = account di sistema/fallback)
├── smtp_host               VARCHAR(255) NOT NULL
├── smtp_port               INTEGER NOT NULL DEFAULT 587
├── smtp_use_tls            BOOLEAN NOT NULL DEFAULT true
├── smtp_username            VARCHAR(255) NOT NULL
├── smtp_password_encrypted VARCHAR(512) NOT NULL
│                           (crittografato con chiave Django SECRET_KEY)
├── email_from              VARCHAR(255) NOT NULL
│                           (es. "Ufficio Acquisti <acquisti@azienda.it>")
├── email_reply_to          VARCHAR(255) NULL
├── attivo                  BOOLEAN NOT NULL DEFAULT true
├── meta                    JSONB NOT NULL DEFAULT '{}'
├── data_insert             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert             TEXT NOT NULL DEFAULT CURRENT_USER
├── data_update             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_update             TEXT NOT NULL DEFAULT CURRENT_USER
```

Vincoli:
  - UNIQUE su `codice`
  - FK su `unita_organizzativa_id` → `config.unita_organizzative(id)`
  - Un solo account con `unita_organizzativa_id IS NULL` per `codice_contesto` di sistema
  - CHECK: `smtp_port BETWEEN 1 AND 65535`

- [x] 1.1.2 — Creare tabella `config.email_template` ✅ `20260328-14`

```
config.email_template
├── id                      SERIAL PK
├── codice                  VARCHAR(100) NOT NULL
│                           (es. 'INVITO_OPERATORE', 'RESET_PASSWORD', 'COMUNICAZIONE_PRATICA')
├── unita_organizzativa_id  INTEGER NULL FK → config.unita_organizzative(id)
│                           (NULL = template di sistema/default)
├── tipo_prestazione_id     INTEGER NULL FK → pratiche.tipi_prestazione(id)
│                           (NULL = generico, non legato a un tipo prestazione specifico)
├── lingua                  VARCHAR(5) NOT NULL DEFAULT 'it'
├── oggetto                 TEXT NOT NULL
│                           (supporta variabili: "Benvenuto {{nome}} in {{azienda}}")
├── corpo_html              TEXT NOT NULL
│                           (template HTML con variabili {{...}})
├── corpo_testo             TEXT NULL
│                           (versione plaintext, fallback se HTML non supportato)
├── attivo                  BOOLEAN NOT NULL DEFAULT true
├── meta                    JSONB NOT NULL DEFAULT '{}'
├── data_insert             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert             TEXT NOT NULL DEFAULT CURRENT_USER
├── data_update             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_update             TEXT NOT NULL DEFAULT CURRENT_USER
```

Vincoli:
  - UNIQUE su `(codice, unita_organizzativa_id, tipo_prestazione_id, lingua)` — permette override per reparto+tipo pratica+lingua
  - FK su `tipo_prestazione_id` → `pratiche.tipi_prestazione(id)`
  - FK su `unita_organizzativa_id`

- [x] 1.1.3 — Creare tabella `config.email_log` ✅ `20260328-15`

```
config.email_log
├── id                      BIGSERIAL PK
├── email_account_id        INTEGER NULL FK → config.email_account(id)
├── email_template_id       INTEGER NULL FK → config.email_template(id)
├── destinatario            VARCHAR(255) NOT NULL
├── oggetto                 TEXT NOT NULL
├── stato                   VARCHAR(20) NOT NULL DEFAULT 'PENDING'
│                           ('PENDING', 'SENT', 'FAILED', 'RETRY')
├── errore                  TEXT NULL
├── tentativi               INTEGER NOT NULL DEFAULT 0
├── max_tentativi           INTEGER NOT NULL DEFAULT 3
├── prossimo_tentativo      TIMESTAMPTZ NULL
├── inviato_at              TIMESTAMPTZ NULL
├── contesto_json           JSONB NOT NULL DEFAULT '{}'
│                           (variabili usate per il rendering)
├── auth_user_id            INTEGER NULL
│                           (operatore destinatario, se applicabile)
├── tx_id                   UUID NULL
├── data_insert             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert             TEXT NOT NULL DEFAULT CURRENT_USER
```

- [x] 1.1.4 — Creare tabella `config.email_outbox` ✅ `20260328-16`

Bozze email preparate dal sistema e modificabili dall'operatore prima dell'invio.
Flusso: template renderizzato → bozza editabile → conferma invio → email_log.

```
config.email_outbox
├── id                      BIGSERIAL PK
├── email_account_id        INTEGER NULL FK → config.email_account(id)
├── email_template_id       INTEGER NULL FK → config.email_template(id)
│                           (template di origine, per riferimento)
├── ambito                  VARCHAR(20) NOT NULL DEFAULT 'SISTEMA'
│                           ('SISTEMA', 'REPARTO', 'OPERATORE')
│                           Determina la visibilità:
│                             SISTEMA   → solo ADMIN
│                             REPARTO   → operatori dell'unità org. + ADMIN
│                             OPERATORE → solo chi l'ha creata + ADMIN
├── unita_organizzativa_id  INTEGER NULL FK → config.unita_organizzative(id)
│                           (obbligatorio se ambito = REPARTO)
├── pratica_id              BIGINT NULL FK → pratiche.pratiche(id)
│                           (se collegata a una pratica — visibile dalla scheda pratica)
├── destinatario            VARCHAR(255) NOT NULL
├── destinatari_cc          TEXT[] NULL
│                           (array di indirizzi CC)
├── oggetto                 TEXT NOT NULL
│                           (pre-compilato dal template, editabile)
├── corpo_html              TEXT NOT NULL
│                           (pre-compilato e renderizzato, editabile)
├── corpo_testo             TEXT NULL
│                           (versione plaintext, editabile)
├── stato                   VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
│                           ('DRAFT', 'READY', 'SENT', 'CANCELLED')
├── contesto_json           JSONB NOT NULL DEFAULT '{}'
│                           (variabili usate per il rendering iniziale)
├── auth_user_id            INTEGER NULL
│                           (operatore destinatario, se applicabile)
├── creato_da_user_id       INTEGER NULL
│                           (operatore che ha creato la bozza)
├── inviato_at              TIMESTAMPTZ NULL
├── email_log_id            BIGINT NULL FK → config.email_log(id)
│                           (collegamento al log dopo invio effettivo)
├── tx_id                   UUID NULL
├── meta                    JSONB NOT NULL DEFAULT '{}'
├── data_insert             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert             TEXT NOT NULL DEFAULT CURRENT_USER
├── data_update             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_update             TEXT NOT NULL DEFAULT CURRENT_USER
```

Vincoli:
  - CHECK: `stato IN ('DRAFT', 'READY', 'SENT', 'CANCELLED')`
  - CHECK: `ambito IN ('SISTEMA', 'REPARTO', 'OPERATORE')`
  - CHECK: `ambito = 'REPARTO' → unita_organizzativa_id IS NOT NULL`
  - FK su `email_account_id`, `email_template_id`, `email_log_id`, `pratica_id`, `unita_organizzativa_id`
  - INDEX su `(stato, creato_da_user_id)` per lista bozze operatore
  - INDEX su `pratica_id` per consultazione dalla scheda pratica
  - INDEX su `(ambito, unita_organizzativa_id)` per filtro reparto

- [x] 1.1.5 — Creare tabella `config.email_allegato` ✅ `20260328-17`

Allegati associati a una bozza outbox. Supporta sia allegati caricati dall'operatore
sia allegati di default del template (es. guida utente PDF, policy aziendale).

```
config.email_allegato
├── id                      BIGSERIAL PK
├── email_outbox_id         BIGINT NULL FK → config.email_outbox(id) ON DELETE CASCADE
├── email_log_id            BIGINT NULL FK → config.email_log(id)
│                           (popolato dopo invio, per consultazione storica)
├── nome_file               VARCHAR(255) NOT NULL
│                           (nome originale del file, es. "guida-utente.pdf")
├── mime_type               VARCHAR(100) NOT NULL
│                           (es. "application/pdf", "image/png")
├── dimensione_bytes        BIGINT NOT NULL
├── file_path               VARCHAR(512) NOT NULL
│                           (percorso relativo nello storage, es. "email_attachments/2026/03/uuid.pdf")
├── origine                 VARCHAR(20) NOT NULL DEFAULT 'UPLOAD'
│                           ('UPLOAD' = caricato dall'operatore, 'TEMPLATE' = default del template)
├── meta                    JSONB NOT NULL DEFAULT '{}'
├── data_insert             TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert             TEXT NOT NULL DEFAULT CURRENT_USER
```

Vincoli:
  - CHECK: `origine IN ('UPLOAD', 'TEMPLATE')`
  - CHECK: `dimensione_bytes > 0`
  - CHECK: almeno uno tra `email_outbox_id` e `email_log_id` NOT NULL
  - INDEX su `email_outbox_id`, INDEX su `email_log_id`

- [x] 1.1.6 — Aggiornare tabella `config.email_log` — colonne corpo inviato ✅ incluso in `20260328-15`

Aggiungere colonne per conservare il testo esattamente come inviato (dopo eventuali
modifiche manuali dall'outbox), per consultazione post-invio fedele:

```sql
ALTER TABLE config.email_log
  ADD COLUMN corpo_inviato_html  TEXT NULL,
  ADD COLUMN corpo_inviato_testo TEXT NULL,
  ADD COLUMN destinatari_cc      TEXT[] NULL,
  ADD COLUMN email_outbox_id     BIGINT NULL
    REFERENCES config.email_outbox(id),
  ADD COLUMN ambito              VARCHAR(20) NOT NULL DEFAULT 'SISTEMA'
    CHECK (ambito IN ('SISTEMA', 'REPARTO', 'OPERATORE')),
  ADD COLUMN unita_organizzativa_id INTEGER NULL
    REFERENCES config.unita_organizzative(id),
  ADD COLUMN pratica_id          BIGINT NULL
    REFERENCES pratiche.pratiche(id);

COMMENT ON COLUMN config.email_log.corpo_inviato_html
  IS 'Corpo HTML esattamente come inviato (dopo eventuali modifiche manuali)';
COMMENT ON COLUMN config.email_log.corpo_inviato_testo
  IS 'Corpo plaintext esattamente come inviato';
COMMENT ON COLUMN config.email_log.destinatari_cc
  IS 'Indirizzi CC usati nell''invio';
COMMENT ON COLUMN config.email_log.email_outbox_id
  IS 'FK bozza di origine (NULL se invio diretto senza anteprima)';
COMMENT ON COLUMN config.email_log.ambito
  IS 'Ambito visibilita'': SISTEMA (solo admin), REPARTO (operatori UO), OPERATORE (solo creatore)';
COMMENT ON COLUMN config.email_log.unita_organizzativa_id
  IS 'Reparto proprietario (obbligatorio se ambito=REPARTO)';
COMMENT ON COLUMN config.email_log.pratica_id
  IS 'Pratica collegata (consultabile dalla scheda pratica)';

CREATE INDEX ix_email_log_pratica_id ON config.email_log(pratica_id);
CREATE INDEX ix_email_log_ambito_uo ON config.email_log(ambito, unita_organizzativa_id);
```

- [x] 1.1.7 — Seed dati: account di sistema (codice `SISTEMA`) e template base ✅ `20260329-60`, `20260329-61`
  - Template `INVITO_OPERATORE`
  - Template `RESET_PASSWORD`
  - Template `CAMBIO_PASSWORD_CONFERMA`
  - Template `NOTIFICA_GENERICA`

#### Backend

- [x] 1.1.8 — Creare `apps/core/services/email_service.py` — `EmailDispatchService` ✅

Responsabilità:
  - `resolve_account(unita_organizzativa_id=None)` → trova account email:
    1. Se `unita_organizzativa_id` fornito → cerca account del reparto
    2. Fallback → account con codice `SISTEMA`
  - `resolve_template(codice, unita_organizzativa_id=None, tipo_prestazione_id=None, lingua='it')` → trova template:
    1. Template specifico per reparto+tipo pratica+lingua
    2. Fallback → template reparto+lingua (senza tipo pratica)
    3. Fallback → template sistema+tipo pratica+lingua
    4. Fallback → template di sistema per lingua
    5. Fallback → template di sistema lingua `it`
  - `render_template(template, variabili: dict)` → sostituisce `{{chiave}}` con valori
  - `send_email(codice_template, destinatario, variabili, unita_organizzativa_id=None, tipo_prestazione_id=None, ambito='SISTEMA', pratica_id=None)`:
    1. Risolve account e template (con tipo_prestazione_id)
    2. Renderizza oggetto e corpo
    3. Crea record in `config.email_log` con stato `PENDING`, ambito, pratica_id
    4. Tenta invio SMTP (con allegati se presenti)
    5. Salva corpo inviato in `corpo_inviato_html` / `corpo_inviato_testo`
    6. Aggiorna stato (`SENT` o `FAILED`)
  - `send_from_outbox(outbox_id)` — invia una bozza confermata:
    1. Legge bozza da `email_outbox` (stato `READY`)
    2. Crea record `email_log` con corpo dalla bozza (non dal template),
       propagando `ambito`, `unita_organizzativa_id`, `pratica_id` dalla bozza
    3. Allega file da `email_allegato`
    4. Aggiorna bozza: `stato = 'SENT'`, `email_log_id = <id>`
    5. Copia allegati su `email_log_id`
  - `retry_failed()` — riprocessa email `FAILED` con `tentativi < max_tentativi`

- [x] 1.1.9 — Creare `apps/core/services/email_outbox_service.py` — `EmailOutboxService` ✅

Responsabilità:
  - `prepare_draft(codice_template, destinatario, variabili, unita_organizzativa_id=None, tipo_prestazione_id=None, creato_da_user_id=None, ambito='SISTEMA', pratica_id=None)`:
    1. Risolve account e template (con tipo_prestazione_id per specializzazione)
    2. Renderizza oggetto e corpo con variabili
    3. Crea record in `config.email_outbox` con stato `DRAFT`, ambito, pratica_id
    4. Ritorna bozza con id, oggetto, corpo renderizzato (editabili dal frontend)
  - `update_draft(outbox_id, oggetto=None, corpo_html=None, corpo_testo=None, destinatari_cc=None)`:
    1. Verifica stato `DRAFT`
    2. Aggiorna i campi modificati
  - `confirm_draft(outbox_id)`:
    1. Verifica stato `DRAFT` → imposta `READY`
    2. Chiama `EmailDispatchService.send_from_outbox(outbox_id)`
  - `cancel_draft(outbox_id)`:
    1. Imposta stato `CANCELLED`
    2. Elimina allegati fisici (cleanup storage)
  - `add_attachment(outbox_id, file, origine='UPLOAD')`:
    1. Valida file (tipo MIME, dimensione max configurabile)
    2. Salva su storage (path: `email_attachments/YYYY/MM/<uuid>.<ext>`)
    3. Crea record `email_allegato`
  - `remove_attachment(allegato_id)`:
    1. Elimina file fisico + record DB
  - `list_drafts(creato_da_user_id=None, stato=None)`:
    1. Lista bozze con filtri

- [x] 1.1.10 — Creare `apps/core/db/email_repository.py`

Responsabilità:
  - Query su `config.email_account`, `config.email_template`, `config.email_log`
  - Query su `config.email_outbox`, `config.email_allegato`
  - Decriptazione password SMTP (usando `django.core.signing` o `Fernet`)
  - Insert/update `email_log`, `email_outbox`, `email_allegato`

- [x] 1.1.11 — Creare management command `send_pending_emails`
  - Processa email con stato `PENDING` o `RETRY`
  - Eseguibile come cron job (pgAgent o crontab)
  - Flag `--dry-run` per preview

- [x] 1.1.12 — Configurare `EMAIL_BACKEND` in settings.py
  - Default: `django.core.mail.backends.smtp.EmailBackend`
  - Dev/test: `django.core.mail.backends.console.EmailBackend`
  - Il service NON usa il backend globale Django ma connessioni SMTP per-account
  - Configurazione storage allegati: `EMAIL_ATTACHMENTS_ROOT`, `EMAIL_ATTACHMENT_MAX_SIZE_MB`

- [x] 1.1.13 — API admin per gestione account email (CRUD)
  - `GET/POST /api/v1/amm-software/email-accounts/`
  - `GET/PUT/DELETE /api/v1/amm-software/email-accounts/<id>/`
  - Solo ruolo ADMIN
  - La password SMTP viene accettata in chiaro e salvata crittografata

- [x] 1.1.14 — API admin per gestione template email (CRUD)
  - `GET/POST /api/v1/amm-software/email-templates/`
  - `GET/PUT/DELETE /api/v1/amm-software/email-templates/<id>/`
  - Solo ruolo ADMIN
  - Endpoint preview: `POST .../preview/` con variabili di esempio

- [x] 1.1.15 — API outbox email (preparazione, modifica, invio bozze)
  - `POST /api/v1/email/prepare/` — prepara bozza da template + variabili, ritorna draft editabile
    - Accetta: `ambito`, `pratica_id`, `tipo_prestazione_id` per specializzazione
  - `GET /api/v1/email/outbox/` — lista bozze visibili all'operatore
    - Filtri: stato, date, ambito, pratica_id
    - Regole visibilita':
      - ADMIN → vede tutte
      - Operatore → vede le proprie (ambito=OPERATORE) + quelle del suo reparto (ambito=REPARTO, stessa UO)
  - `GET /api/v1/email/outbox/<id>/` — dettaglio bozza con allegati
  - `PUT /api/v1/email/outbox/<id>/` — modifica oggetto, corpo, CC
  - `POST /api/v1/email/outbox/<id>/send/` — conferma e invia
  - `POST /api/v1/email/outbox/<id>/cancel/` — annulla bozza
  - Permessi: operatore autenticato (le proprie bozze + reparto) o ADMIN (tutte)

- [x] 1.1.16 — API allegati email
  - `POST /api/v1/email/outbox/<id>/allegati/` — upload allegato (multipart)
  - `GET /api/v1/email/outbox/<id>/allegati/` — lista allegati della bozza
  - `DELETE /api/v1/email/allegati/<allegato_id>/` — rimuovi allegato
  - `GET /api/v1/email/allegati/<allegato_id>/download/` — download file
  - Validazione: tipo MIME whitelist, dimensione max, numero max allegati per email
  - Stesso endpoint download usabile per allegati da `email_log` (consultazione storica)

- [x] 1.1.17 — API consultazione log email (migliorata, con visibilita' per ambito)
  - `GET /api/v1/email/log/` — log email visibili all'operatore
    - Filtri: stato, destinatario, date, ambito, pratica_id, unita_organizzativa_id
    - Regole visibilita' (stesse dell'outbox):
      - ADMIN → vede tutte
      - Operatore → vede le proprie (ambito=OPERATORE) + quelle del suo reparto (ambito=REPARTO, stessa UO)
      - Le email con `pratica_id` sono visibili anche a chi ha accesso alla pratica
  - `GET /api/v1/email/log/<id>/` — dettaglio con corpo inviato + allegati
  - `POST /api/v1/email/log/<id>/reinvia/` — re-invia email (crea nuova bozza outbox pre-compilata dalla mail originale)
  - `GET /api/v1/amm-software/email-log/` — endpoint admin: vede tutto, senza filtro ambito (retrocompatibile)

#### Frontend

- [x] 1.1.18 — Pannello admin: gestione account email
  - Lista account con stato attivo/inattivo
  - Form creazione/modifica con test connessione SMTP
  - Associazione a reparto (autocomplete unità organizzativa)

- [x] 1.1.19 — Pannello admin: gestione template email
  - Lista template raggruppati per codice
  - Editor con preview HTML
  - Indicazione variabili disponibili per tipo template

- [x] 1.1.20 — Dialog/drawer "Componi email" (componente riutilizzabile)

Componente che si apre quando un'azione genera un invio email (invito operatore,
reset password, notifica generica). Flusso UX:

```
Azione utente (es. "Invia invito")
  → API prepare → bozza creata
  → Dialog si apre con:
    ┌─────────────────────────────────────────────┐
    │  Componi email                          [X] │
    ├─────────────────────────────────────────────┤
    │  Da: Ufficio Acquisti <acq@azienda.it>  [i] │
    │  A:  mario.rossi@azienda.it                 │
    │  CC: [+ aggiungi]                           │
    │  Oggetto: [Benvenuto Mario in ZeroErp    ]  │
    ├─────────────────────────────────────────────┤
    │  [Editor HTML/testo con toolbar base]        │
    │  Corpo pre-compilato dal template,           │
    │  editabile dall'operatore                    │
    ├─────────────────────────────────────────────┤
    │  Allegati:                                   │
    │  📎 guida-utente.pdf (1.2 MB) [x]           │
    │  [+ Aggiungi allegato]                       │
    ├─────────────────────────────────────────────┤
    │         [Annulla]  [Invia email]             │
    └─────────────────────────────────────────────┘
```

Caratteristiche:
  - Oggetto e corpo pre-compilati e modificabili
  - Editor HTML semplice (grassetto, corsivo, link, liste) — usare componente PrimeVue `Editor` o libreria leggera
  - Toggle HTML/plaintext per vedere entrambe le versioni
  - Upload allegati drag & drop (con progress bar)
  - Indicazione account mittente (non editabile, risolto dal backend)
  - Pulsante "Invia" chiama `POST .../send/`, "Annulla" chiama `POST .../cancel/`

- [x] 1.1.21 — Consultazione log email (con visibilita' per ambito)
  - Tabella con filtri: stato, destinatario, data, template, **ambito, reparto, pratica**
  - Visibilita' automatica: l'operatore vede solo le sue + quelle del reparto
  - Dettaglio email inviata con:
    - Corpo HTML esattamente come inviato (render in iframe/panel)
    - Lista allegati con download
    - Metadati: account mittente, template usato, variabili, timestamp
    - Badge ambito: "Sistema" / "Reparto Acquisti" / "Personale"
    - Link alla pratica collegata (se presente)
  - Pulsante "Re-invia" → crea nuova bozza outbox pre-compilata dalla mail originale
  - Pulsante "Esporta" → download email come .eml (opzionale, bassa priorità)

- [x] 1.1.22 — Tab "Comunicazioni" nel drawer pratica
  - Lista email inviate nel contesto della pratica (`pratica_id`)
  - Ordinate per data, con stato e destinatario
  - Click → apre dettaglio email (corpo inviato + allegati)
  - Pulsante "Nuova comunicazione" → apre dialog Componi email (1.1.20)
    con `pratica_id` pre-impostato, template risolto per tipo pratica + reparto

#### Test

- [x] 1.1.T1 — Test Django: `EmailDispatchService` con mock SMTP
- [x] 1.1.T2 — Test Django: risoluzione account per reparto con fallback
- [x] 1.1.T3 — Test Django: risoluzione template per reparto+lingua con fallback
- [x] 1.1.T4 — Test Django: rendering template con variabili
- [x] 1.1.T5 — Test Django: retry email fallite
- [x] 1.1.T6 — Test Django: `EmailOutboxService.prepare_draft` → bozza creata con corpo renderizzato
- [x] 1.1.T7 — Test Django: modifica bozza (oggetto, corpo, CC) → campi aggiornati
- [x] 1.1.T8 — Test Django: conferma e invio bozza → stato SENT + email_log creato con corpo inviato
- [x] 1.1.T9 — Test Django: annullamento bozza → stato CANCELLED + allegati eliminati
- [x] 1.1.T10 — Test Django: upload allegato → file salvato + record creato
- [x] 1.1.T11 — Test Django: validazione allegato (tipo MIME non consentito, dimensione eccessiva → errore)
- [x] 1.1.T12 — Test Django: invio con allegati → email contiene attachment MIME
- [x] 1.1.T13 — Test Django: re-invio da log → nuova bozza pre-compilata con corpo/allegati originali
- [x] 1.1.T14 — Test Django: consultazione log con corpo inviato fedele (non ri-renderizzato)

---

### 1.2 BB-2: Token Monouso Generico

#### Concetto

Un meccanismo unico per generare token sicuri, monouso, con scadenza,
riutilizzabile per qualsiasi flusso: invito operatore, reset password,
conferma email, attivazione account, ecc.

```
TokenService.create(
    tipo='RESET_PASSWORD',
    auth_user_id=42,
    scadenza_ore=24,
    meta={'invitato_da': 'admin'}
)
→ token: "a1b2c3d4..." (hash SHA-256, 64 chars)
→ record in config.token_monouso
```

#### DB

- [x] 1.2.1 — Creare tabella `config.token_monouso` ✅ `20260328-18`

```
config.token_monouso
├── id                  BIGSERIAL PK
├── token_hash          VARCHAR(128) UNIQUE NOT NULL
│                       (SHA-256 del token — il token in chiaro NON viene salvato)
├── tipo                VARCHAR(50) NOT NULL
│                       ('INVITO_OPERATORE', 'RESET_PASSWORD', 'CONFERMA_EMAIL', ...)
├── auth_user_id        INTEGER NOT NULL FK → auth_user(id)
├── scadenza            TIMESTAMPTZ NOT NULL
├── utilizzato          BOOLEAN NOT NULL DEFAULT false
├── utilizzato_at       TIMESTAMPTZ NULL
├── ip_utilizzo         INET NULL
├── meta                JSONB NOT NULL DEFAULT '{}'
├── data_insert         TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert         TEXT NOT NULL DEFAULT CURRENT_USER
```

Vincoli:
  - UNIQUE su `token_hash`
  - INDEX su `(tipo, auth_user_id, utilizzato)` per lookup rapido
  - CHECK: `scadenza > data_insert`

- [x] 1.2.2 — Creare funzione `config.fn_cleanup_token_scaduti()` ✅ `20260328-24`
  - Elimina token scaduti o utilizzati da più di N giorni (configurabile)
  - Eseguibile come job pgAgent periodico

#### Backend

- [x] 1.2.3 — Creare `apps/core/services/token_service.py` — `TokenService`

Responsabilità:
  - `create(tipo, auth_user_id, scadenza_ore=24, meta=None)`:
    1. Genera token casuale (32 bytes → 64 hex)
    2. Salva SHA-256 del token in DB
    3. Invalida eventuali token precedenti dello stesso tipo per lo stesso utente
    4. Ritorna il token in chiaro (unica volta)
  - `validate(token, tipo)`:
    1. Calcola SHA-256 del token ricevuto
    2. Cerca in DB: hash match + tipo + non utilizzato + non scaduto
    3. Se valido → ritorna `auth_user_id` e `meta`
    4. Se invalido → `None`
  - `consume(token, tipo, ip=None)`:
    1. Valida + segna come utilizzato + salva IP e timestamp
    2. Ritorna `auth_user_id` o errore
  - `invalidate_all(tipo, auth_user_id)`:
    1. Segna come utilizzati tutti i token di quel tipo/utente

- [x] 1.2.4 — Creare `apps/core/db/token_repository.py`
  - Query su `config.token_monouso`
  - Insert, update stato, cleanup

#### Test

- [x] 1.2.T1 — Test Django: creazione token + validazione
- [x] 1.2.T2 — Test Django: token scaduto → rifiutato
- [x] 1.2.T3 — Test Django: token già utilizzato → rifiutato
- [x] 1.2.T4 — Test Django: invalidazione token precedenti dello stesso tipo

---

### 1.3 BB-3: Cambio Password Obbligatorio

#### Concetto

Quando un operatore deve cambiare la password (primo accesso, reset admin, scadenza policy),
il login restituisce un flag `password_change_required: true`. Il frontend blocca la navigazione
e mostra la pagina di cambio password.

#### DB

- [x] 1.3.1 — Aggiungere colonna a `anagrafiche.risorse_umane_auth_user`: ✅ `20260328-19`

```sql
ALTER TABLE anagrafiche.risorse_umane_auth_user
  ADD COLUMN deve_cambiare_password BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN anagrafiche.risorse_umane_auth_user.deve_cambiare_password
  IS 'Se true, l''operatore deve cambiare password al prossimo login';
```

- [x] 1.3.2 — Aggiornare `script.fn_get_user_profile()`: ✅ `20260328-26`
  - Includere `deve_cambiare_password` nel JSONB di risposta

#### Backend

- [x] 1.3.3 — Modificare `AuditTokenObtainPairView` (auth_views.py):
  - Dopo login riuscito, leggere `deve_cambiare_password`
  - Se `true` → aggiungere al response JSON: `password_change_required: true`
  - Il token viene comunque rilasciato (serve per chiamare l'endpoint cambio password)

- [x] 1.3.4 — Creare endpoint `POST /api/v1/auth/change-password/`
  - File: `apps/core/api/change_password_view.py`
  - Input: `{ old_password, new_password, new_password_confirm }`
  - Validazioni:
    - Utente autenticato (JWT)
    - `old_password` corretta
    - `new_password` passa i 4 validators Django
    - `new_password != old_password`
    - `new_password == new_password_confirm`
  - Azioni:
    1. `user.set_password(new_password)`
    2. `user.save()`
    3. Reset flag `deve_cambiare_password = false`
    4. Blacklist tutti i refresh token precedenti
    5. Genera nuova coppia access+refresh
    6. Log audit: `PASSWORD_CHANGED`
  - Response: `{ access, refresh }` (nuovi token)

- [x] 1.3.5 — Creare middleware/permission per blocco navigazione
  - Se `deve_cambiare_password = true`, gli unici endpoint consentiti sono:
    - `POST /api/v1/auth/change-password/`
    - `POST /api/v1/auth/logout/`
    - `GET /api/v1/core/me/`
  - Tutti gli altri → HTTP 403 con codice `E_CAMBIO_PASSWORD_RICHIESTO`

#### Frontend

- [x] 1.3.6 — Creare pagina `ChangePasswordView.vue`
  - Route: `/change-password` (pubblica per utenti autenticati)
  - Form: password attuale, nuova password, conferma nuova password
  - Indicatore forza password in tempo reale
  - Validazione client-side (lunghezza minima, match conferma)
  - Al successo: aggiorna token nello store e redirect a home

- [x] 1.3.7 — Modificare `auth.js` store:
  - Salvare `passwordChangeRequired` dallo stato login
  - Getter `mustChangePassword`

- [x] 1.3.8 — Modificare route guard (router/index.js):
  - Se `mustChangePassword === true` → redirect forzato a `/change-password`
  - Bloccare navigazione a qualsiasi altra rotta

- [x] 1.3.9 — Aggiungere link "Cambia password" nel menu profilo utente
  - Accessibile sempre (non solo quando obbligatorio)

#### Test

- [x] 1.3.T1 — Test Django: login con `deve_cambiare_password=true` → flag nel response
- [x] 1.3.T2 — Test Django: cambio password con validazioni
- [x] 1.3.T3 — Test Django: middleware blocca navigazione se flag attivo
- [x] 1.3.T4 — Test Django: dopo cambio password, flag resettato

---

## Fase 2 — Reset Password Dimenticata

> **Obiettivo**: permettere all'operatore di resettare la password via email,
> senza intervento admin.
> **Dipende da**: BB-1 (email), BB-2 (token monouso), BB-3 (cambio password)

### DB

- [x] 2.1 — Nessuna modifica DB aggiuntiva
  - Usa `config.token_monouso` con tipo `RESET_PASSWORD`
  - Usa `config.email_template` con codice `RESET_PASSWORD`

### Backend

- [x] 2.2 — Creare endpoint `POST /api/v1/auth/password-reset-request/`
  - File: `apps/core/api/password_reset_view.py`
  - Input: `{ email }`
  - **Non autenticato** (endpoint pubblico)
  - Rate limiting: `PasswordResetRateThrottle` (3 richieste / 15 minuti per IP)
  - Logica:
    1. Cerca `auth_user` con quella email
    2. Se trovato e attivo:
       - Crea token monouso tipo `RESET_PASSWORD` (scadenza 1 ora)
       - Risolve reparto dell'operatore → sceglie account email mittente
       - Invia email con template `RESET_PASSWORD` e link:
         `{FRONTEND_URL}/reset-password/{token}`
       - **Invio diretto** (senza outbox/anteprima — è self-service, non ci sono operatori coinvolti)
    3. Se NON trovato → **risponde comunque 200** (sicurezza: non rivelare email esistenti)
  - Response: `{ message: "Se l'email è registrata, riceverai un link" }`

- [x] 2.3 — Creare endpoint `POST /api/v1/auth/password-reset-confirm/`
  - Input: `{ token, new_password, new_password_confirm }`
  - **Non autenticato**
  - Logica:
    1. `TokenService.consume(token, 'RESET_PASSWORD', ip=request_ip)`
    2. Se valido → `user.set_password(new_password)`, reset flag `deve_cambiare_password`
    3. Blacklist tutti i refresh token dell'utente
    4. Invia email conferma con template `CAMBIO_PASSWORD_CONFERMA`
    5. Log audit: `PASSWORD_RESET`
  - Response: `{ message: "Password aggiornata" }` (senza token — deve ri-loggarsi)

- [x] 2.4 — Creare endpoint `GET /api/v1/auth/password-reset-validate/{token}/`
  - **Non autenticato**
  - Verifica se il token è ancora valido (senza consumarlo)
  - Usato dal frontend per mostrare il form o un messaggio di errore/scadenza

### Frontend

- [x] 2.5 — Aggiungere link "Password dimenticata?" nella `LoginView.vue`

- [x] 2.6 — Creare pagina `PasswordResetRequestView.vue`
  - Route: `/password-reset` (pubblica)
  - Form: solo campo email
  - Messaggio di conferma generico (non rivela se email esiste)

- [x] 2.7 — Creare pagina `PasswordResetConfirmView.vue`
  - Route: `/reset-password/:token` (pubblica)
  - All'apertura: chiama endpoint validate per verificare token
  - Se token valido → form nuova password + conferma
  - Se token invalido/scaduto → messaggio errore + link a nuova richiesta
  - Al successo → redirect a login con messaggio

### Test

- [x] 2.T1 — Test Django: richiesta reset con email esistente → token creato + email accodata
- [x] 2.T2 — Test Django: richiesta reset con email inesistente → 200 (nessun token)
- [x] 2.T3 — Test Django: conferma reset con token valido → password cambiata
- [x] 2.T4 — Test Django: conferma reset con token scaduto → errore
- [x] 2.T5 — Test Django: rate limiting richieste reset

---

## Fase 3 — Invito Operatore al Primo Accesso

> **Obiettivo**: quando l'admin abilita un operatore, il sistema invia
> automaticamente un'email di invito con link di attivazione.
> **Dipende da**: BB-1 (email), BB-2 (token), BB-3 (cambio password), Fase 2

### DB

- [x] 3.1 — Aggiungere colonna a `anagrafiche.risorse_umane_auth_user`: ✅ incluso in `20260328-19`

```sql
ALTER TABLE anagrafiche.risorse_umane_auth_user
  ADD COLUMN invito_inviato_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN anagrafiche.risorse_umane_auth_user.invito_inviato_at
  IS 'Timestamp ultimo invito inviato all''operatore (NULL = mai invitato)';
```

- [x] 3.2 — Creare funzione `script.fn_check_operatore_invitabile(p_auth_user_id)` ✅ `20260328-25`
  - Verifica: utente esiste, è attivo, ha email, non ha mai effettuato login
  - Ritorna JSONB con `{invitabile: bool, motivo: text, email: text}`

### Backend

- [x] 3.3 — Creare `apps/anagrafiche/services/invito_operatore_service.py`

Responsabilità:
  - `prepara_invito(auth_user_id, invitato_da_user_id)`:
    1. Verifica operatore invitabile (fn_check_operatore_invitabile)
    2. Imposta password casuale temporanea (`User.set_password(random)`)
    3. Imposta `deve_cambiare_password = true`
    4. Crea token monouso tipo `INVITO_OPERATORE` (scadenza 72 ore)
    5. Risolve reparto dell'operatore → account email mittente
    6. **Crea bozza outbox** con template `INVITO_OPERATORE`:
       - Link: `{FRONTEND_URL}/attivazione/{token}`
       - Variabili: nome, cognome, azienda, ruolo, invitato_da
    7. Ritorna `outbox_id` per anteprima/modifica frontend
  - `conferma_invito(outbox_id, invitato_da_user_id)`:
    1. Chiama `EmailOutboxService.confirm_draft(outbox_id)` → invio effettivo
    2. Aggiorna `invito_inviato_at`
    3. Log audit: `INVITO_INVIATO`
  - `reinvia_invito(auth_user_id, invitato_da_user_id)`:
    1. Invalida token precedenti tipo `INVITO_OPERATORE`
    2. Riesegue `prepara_invito`

- [x] 3.4 — Creare endpoint admin `POST /api/v1/amm-software/operatori/<id>/invita/`
  - Solo ruolo ADMIN
  - Chiama `invito_operatore_service.prepara_invito()`
  - Response: `{ outbox_id: 123, email: "m***@azienda.it" }` (bozza pronta per anteprima)
  - Il frontend apre il dialog "Componi email" (1.1.20) con la bozza editabile
  - L'invio effettivo avviene quando l'admin conferma dal dialog

- [x] 3.5 — Creare endpoint admin `POST /api/v1/amm-software/operatori/<id>/reinvia-invito/`
  - Solo ruolo ADMIN
  - Per rinviare invito scaduto o non ricevuto
  - Stessa logica: prepara bozza → anteprima → conferma

- [x] 3.6 — Creare endpoint pubblico `POST /api/v1/auth/attivazione/`
  - Input: `{ token, new_password, new_password_confirm }`
  - Logica:
    1. `TokenService.consume(token, 'INVITO_OPERATORE')`
    2. `user.set_password(new_password)` con validazione
    3. Reset `deve_cambiare_password = false`
    4. Log audit: `ACCOUNT_ATTIVATO`
  - Response: `{ message: "Account attivato" }` (deve ri-loggarsi)

- [x] 3.7 — Opzionale: trigger automatico invio invito
  - Quando admin imposta `is_active = true` su un operatore mai loggato
  - Via signal Django o hook nel service di abilitazione esistente

### Frontend

- [x] 3.8 — Creare pagina `AttivazioneView.vue`
  - Route: `/attivazione/:token` (pubblica)
  - Valida token all'apertura
  - Form: nuova password + conferma
  - Messaggio benvenuto personalizzato
  - Al successo → redirect a login

- [x] 3.9 — Aggiungere bottoni nel drawer operatore (amm-software):
  - "Invia invito" (se mai invitato e attivo)
  - "Reinvia invito" (se già invitato)
  - Badge: "Invitato il DD/MM/YYYY" o "Mai invitato"

- [x] 3.10 — Colonna "Stato invito" nella lista operatori
  - Mai invitato / Invitato (data) / Attivato

### Test

- [x] 3.T1 — Test Django: invio invito → token + email + flag
- [x] 3.T2 — Test Django: attivazione con token valido → password impostata
- [x] 3.T3 — Test Django: reinvio invalida token precedente
- [x] 3.T4 — Test Django: invito a operatore non invitabile → errore

---

## Fase 4 — Autenticazione a Due Fattori (2FA TOTP)

> **Obiettivo**: aggiungere autenticazione TOTP opzionale (Google Authenticator, Authy).
> **Dipende da**: Fasi 1-3 completate
> **Nuove dipendenze Python**: `pyotp`, `qrcode`, `Pillow`

### DB

- [x] 4.1 — Creare tabella `config.auth_totp_device` ✅ `20260328-20`

```
config.auth_totp_device
├── id                  BIGSERIAL PK
├── auth_user_id        INTEGER UNIQUE NOT NULL FK → auth_user(id)
│                       (1:1 — un solo device TOTP per utente)
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
├── data_insert         TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert         TEXT NOT NULL DEFAULT CURRENT_USER
├── data_update         TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_update         TEXT NOT NULL DEFAULT CURRENT_USER
```

- [x] 4.2 — Aggiungere colonna a `anagrafiche.risorse_umane_auth_user`: ✅ `20260328-21`

```sql
ALTER TABLE anagrafiche.risorse_umane_auth_user
  ADD COLUMN totp_obbligatorio BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN anagrafiche.risorse_umane_auth_user.totp_obbligatorio
  IS 'Se true, l''operatore DEVE configurare il 2FA per accedere';
```

- [ ] 4.3 — Aggiornare `script.fn_get_user_profile()`: (da fare in Fase 4, richiede tabella `auth_totp_device`)
  - Includere `totp_abilitato` e `totp_obbligatorio` nel JSONB di risposta

### Backend

- [ ] 4.4 — Creare `apps/core/services/totp_service.py` — `TotpService`

Responsabilità:
  - `setup_device(auth_user_id)`:
    1. Genera secret TOTP (`pyotp.random_base32()`)
    2. Salva crittografato in `auth_totp_device`
    3. Genera 10 recovery codes (monouso)
    4. Salva hash dei recovery codes
    5. Ritorna: `{ secret, provisioning_uri, qr_code_base64, recovery_codes }`
  - `confirm_setup(auth_user_id, codice)`:
    1. Verifica codice TOTP con `pyotp.TOTP(secret).verify(codice, valid_window=1)`
    2. Se valido → `confermato = true`, `abilitato = true`
  - `verify(auth_user_id, codice)`:
    1. Anti-replay: rifiuta se `codice == ultimo_codice_usato`
    2. Verifica TOTP
    3. Se fallisce → prova recovery codes
    4. Aggiorna `ultimo_codice_usato` e `ultimo_uso_at`
    5. Ritorna `{valido: bool, tipo: 'totp'|'recovery', recovery_rimanenti: N}`
  - `disable(auth_user_id)`:
    1. Imposta `abilitato = false`
    2. Cancella secret e recovery codes
  - `regenerate_recovery_codes(auth_user_id, codice_totp)`:
    1. Verifica codice TOTP corrente (conferma identità)
    2. Genera nuovi 10 recovery codes
    3. Ritorna in chiaro (unica volta)

- [ ] 4.5 — Modificare flusso login (login a due step):

Step 1 — `POST /api/v1/auth/token/` (esistente, modificato):
  - Login username+password come ora
  - Se 2FA abilitato → NON rilascia token JWT definitivo
  - Risposta: `{ two_factor_required: true, two_factor_token: "<token_temporaneo>" }`
  - Il `two_factor_token` è un token firmato (Django signing) con scadenza 5 minuti
    contenente `auth_user_id` — NON è un JWT

Step 2 — `POST /api/v1/auth/token/2fa-verify/` (nuovo):
  - Input: `{ two_factor_token, code }`
  - Verifica firma e scadenza del token temporaneo
  - Verifica codice TOTP via `TotpService.verify()`
  - Se valido → rilascia coppia JWT (access + refresh) come login normale
  - Se fallisce → errore + log tentativo

- [ ] 4.6 — Creare endpoint profilo 2FA:
  - `POST /api/v1/auth/2fa/setup/` — avvia setup, ritorna QR code
  - `POST /api/v1/auth/2fa/confirm/` — conferma setup con primo codice
  - `POST /api/v1/auth/2fa/disable/` — disabilita (richiede password corrente)
  - `POST /api/v1/auth/2fa/recovery-codes/` — rigenera codici (richiede codice TOTP)

- [ ] 4.7 — Endpoint admin per gestione 2FA operatori:
  - `DELETE /api/v1/amm-software/operatori/<id>/2fa/` — disabilita 2FA (emergenza admin)
  - `PUT /api/v1/amm-software/operatori/<id>/2fa-obbligatorio/` — imposta obbligo
  - Log audit per ogni operazione admin su 2FA

- [ ] 4.8 — Middleware 2FA obbligatorio:
  - Se `totp_obbligatorio = true` e `totp_abilitato = false`:
    - Consenti solo: setup 2FA, logout, me
    - Tutti gli altri → HTTP 403 con codice `E_2FA_SETUP_RICHIESTO`

### Frontend

- [ ] 4.9 — Modificare `LoginView.vue` per flusso a due step:
  - Step 1: username + password (come ora)
  - Se `two_factor_required: true` → mostra campo codice TOTP
  - Step 2: input codice 6 cifre + bottone verifica
  - Link "Usa codice di recupero" → campo testo per recovery code

- [ ] 4.10 — Creare sezione "Sicurezza" nel profilo utente:
  - Stato 2FA: Abilitato/Disabilitato
  - Bottone "Configura 2FA" → wizard setup:
    1. Mostra QR code + secret testuale (per input manuale)
    2. Campo verifica: inserisci codice dall'app
    3. Mostra recovery codes (scaricabili/stampabili)
    4. Conferma: "Ho salvato i codici di recupero"
  - Bottone "Disabilita 2FA" (richiede password)
  - Bottone "Rigenera codici di recupero" (richiede codice TOTP)

- [ ] 4.11 — Aggiungere nel drawer operatore (admin):
  - Badge "2FA Attivo" / "2FA Non configurato" / "2FA Obbligatorio"
  - Bottone "Disabilita 2FA" (emergenza)
  - Toggle "2FA Obbligatorio"

- [ ] 4.12 — Pagina forzata setup 2FA:
  - Se `totp_obbligatorio = true` e non configurato → redirect a setup
  - Simile al blocco cambio password (Fase 1)

### Test

- [ ] 4.T1 — Test Django: setup device → secret + QR + recovery codes
- [ ] 4.T2 — Test Django: conferma setup con codice valido
- [ ] 4.T3 — Test Django: login 2 step completo
- [ ] 4.T4 — Test Django: anti-replay (stesso codice rifiutato)
- [ ] 4.T5 — Test Django: recovery code valido + decremento contatore
- [ ] 4.T6 — Test Django: admin disabilita 2FA operatore
- [ ] 4.T7 — Test Django: middleware 2FA obbligatorio

---

## Riepilogo dipendenze tra fasi

```
Fase 1 (BB-1 Email + BB-2 Token + BB-3 Cambio Password)
  │
  ├──→ Fase 2 (Reset Password)
  │      usa: BB-1 (invio email), BB-2 (token reset), BB-3 (set password)
  │
  └──→ Fase 3 (Invito Operatore)
         usa: BB-1 (invio email), BB-2 (token invito), BB-3 (primo cambio password)
         │
         └──→ Fase 4 (2FA TOTP)
                usa: BB-3 (flag stato credenziali, middleware blocco)
                indipendente da BB-1/BB-2 ma logicamente dopo Fase 3
```

## Nuove dipendenze Python (da aggiungere a requirements.in)

| Fase | Pacchetto | Versione | Scopo |
|------|-----------|----------|-------|
| 1 | (nessuno) | — | Django ha `django.core.mail` + `django.core.signing` built-in |
| 1 | `cryptography` | >=44.0 | Fernet per crittografia password SMTP e secret TOTP |
| 4 | `pyotp` | >=2.9 | Generazione/verifica codici TOTP |
| 4 | `qrcode` | >=8.0 | Generazione QR code per setup authenticator |
| 4 | `Pillow` | >=11.0 | Dipendenza qrcode per output immagine |

## Confini del sistema email — cosa costruiamo e cosa no

> Questa sezione documenta una scelta architetturale deliberata, presa il 2026-03-28,
> su dove finisce il sistema email di ZeroErp e dove inizia il territorio di strumenti esterni.

### Cosa costruiamo (punti 1-7)

Il sistema email di ZeroErp copre le esigenze di un ERP in produzione:

| # | Funzionalita' | Esempio |
|---|---|---|
| 1 | **Email transazionali di sistema** | Invito operatore, reset password, conferma 2FA |
| 2 | **Notifiche operative** | Pratica scaduta, SLA in allarme, lotto completato |
| 3 | **Log completo di ogni invio** | Corpo esatto inviato, allegati, destinatari, esito |
| 4 | **Template per reparto/tipo pratica** | Testi diversi per "Reclamo Acquisti" vs "Offerta Commerciale" |
| 5 | **Comunicazioni ad-hoc da pratica** | Operatore scrive al cliente dalla scheda pratica, con anteprima |
| 6 | **Storico comunicativo della pratica** | Dalla pratica si vedono tutte le email inviate nel suo contesto |
| 7 | **Allegati** | Documenti inviati insieme alla email |

Tutto questo e' **solo invio** (SMTP out). L'email e' un canale di uscita, non una casella di posta.

### Cosa NON costruiamo (punti 8-11) — e perche'

| # | Funzionalita' esclusa | Motivazione |
|---|---|---|
| 8 | **Casella di posta in ingresso per reparto** | Richiede IMAP polling/push, parsing MIME, gestione spam, deduplicazione — complessita' enorme per un risultato mediocre rispetto a strumenti dedicati |
| 9 | **Thread di conversazione** | Richiede matching In-Reply-To/References, correlazione mail in ingresso con pratiche — logica di un mail client, non di un ERP |
| 10 | **Ricezione email e associazione automatica a pratiche** | Richiede NLP/regole per capire a quale pratica si riferisce una mail ricevuta — territorio di CRM/ticketing |
| 11 | **Gestione completa CRM/ticketing via email** | Zammad, FreeScout, Chatwoot e simili fanno esattamente questo, con anni di maturita'. Replicarlo dentro l'ERP produce qualcosa di inferiore che va mantenuto per sempre |

### Strategia per il futuro: integrazione via API

L'architettura attuale e' pensata per lasciare la porta aperta:

```
┌─────────────────────┐          ┌─────────────────────────┐
│     ZeroErp         │          │  Sistema esterno         │
│                     │   API    │  (Zammad, FreeScout,     │
│  pratiche.pratiche  │◄────────►│   Chatwoot, ...)         │
│  config.email_log   │          │                          │
│  ambito / pratica_id│          │  Casella ingresso        │
│  unita_organizzativa│          │  Thread conversazioni    │
│                     │          │  Ticketing               │
└─────────────────────┘          └─────────────────────────┘
```

I dati di collegamento ci sono gia':
- **`pratica_id`** su outbox/log → il sistema esterno puo' taggare le sue conversazioni con l'ID pratica ZeroErp
- **`ambito` + `unita_organizzativa_id`** → il sistema esterno puo' mappare i suoi team/inbox ai reparti ZeroErp
- **`email_log`** → quando ZeroErp invia, il sistema esterno puo' leggere il log via API per tenere il thread sincronizzato
- **Webhook** → il sistema esterno puo' notificare ZeroErp quando arriva una risposta (futuro endpoint `POST /api/v1/email/incoming-webhook/`)

Quando servira' il CRM/ticketing, non si butta via niente: si aggiunge un'integrazione
bidirezionale via API. I dati restano nel sistema che li gestisce meglio.

### Nel contesto attuale (2026)

Nel mondo pre-API, l'ERP doveva fare da postino perche' non c'era altro modo.
Oggi le comunicazioni critiche passano per canali dedicati:

- **Fatture** → SDI (gia' nel piano ZeroErp)
- **PEC** → canale legale con regole proprie
- **Ordini/DDT** → portali B2B, EDI
- **Pagamenti** → notifiche bancarie automatiche

L'email resta utile per comunicazioni operative e notifiche, ma non e' piu'
il canale unico. ZeroErp la gestisce per quello che serve (invio + tracciamento),
senza tentare di diventare un mail client.

---

## Note di sicurezza

- **Token in chiaro MAI salvati in DB** — solo hash SHA-256
- **Password SMTP crittografate** con Fernet (chiave derivata da SECRET_KEY)
- **Secret TOTP crittografati** in DB
- **Recovery codes** salvati come hash, mostrati in chiaro solo al momento della generazione
- **Endpoint reset password** risponde sempre 200 (non rivela email esistenti)
- **Anti-replay TOTP**: salva ultimo codice usato, rifiuta duplicati
- **Rate limiting** su tutti gli endpoint pubblici sensibili
- **Audit log** per ogni operazione critica (cambio password, reset, invito, 2FA)
- **Allegati email**: validazione MIME type whitelist, dimensione max configurabile, storage su filesystem (non in DB)
- **Corpo email inviato salvato** in `email_log` per consultazione fedele post-invio (non ri-renderizzato dal template)

---
---

## Appendice A — Riepilogo File DB (Completati)

> Tutti i file di migrazione sono stati creati sul **server DB** il 2026-03-28/29.
> Percorso base: `db/changelog/migrations_v2/`
> I dettagli strutturali (colonne, vincoli, logica) sono nelle sezioni
> 1.1-1.3 del corpo del documento. Qui sotto il riepilogo dei file effettivi.

---

### Tabelle (00_schema)


| # | File | Oggetto | Fase |
| --- | --- | --- | --- |
| 13 | `00_schema/config/20260328-13-create-email-account-mctit.yaml` | `config.email_account` | 1 ✅ |
| 14 | `00_schema/config/20260328-14-create-email-template-mctit.yaml` | `config.email_template` (con `tipo_prestazione_id`) | 1 ✅ |
| 15 | `00_schema/config/20260328-15-create-email-log-mctit.yaml` | `config.email_log` (con ambito, pratica_id, corpo inviato, CC) | 1 ✅ |
| 16 | `00_schema/config/20260328-16-create-email-outbox-mctit.yaml` | `config.email_outbox` (con ambito, pratica_id, FK circolari log) | 1 ✅ |
| 17 | `00_schema/config/20260328-17-create-email-allegato-mctit.yaml` | `config.email_allegato` | 1 ✅ |
| 18 | `00_schema/config/20260328-18-create-token-monouso-mctit.yaml` | `config.token_monouso` | 1 ✅ |
| 19 | `00_schema/anagrafiche/20260328-19-alter-risorse-umane-auth-user-add-auth-flags-mctit.yaml` | ALTER +2 col: `deve_cambiare_password`, `invito_inviato_at` | 1+3 ✅ |
| 20 | `00_schema/config/20260328-20-create-auth-totp-device-mctit.yaml` | `config.auth_totp_device` | 4 ✅ |
| 21 | `00_schema/anagrafiche/20260328-21-alter-risorse-umane-auth-user-add-totp-obbligatorio-mctit.yaml` | ALTER +1 col: `totp_obbligatorio` | 4 ✅ |

### Funzioni (20_code)

| # | File | Oggetto | Fase |
| --- | --- | --- | --- |
| 22 | `20_code/config/20260328-22-create-fn-resolve-email-account-mctit.yaml` | Risoluzione account SMTP con fallback reparto→SISTEMA | 1 ✅ |
| 23 | `20_code/config/20260328-23-create-fn-resolve-email-template-mctit.yaml` | Risoluzione template con fallback 5 livelli | 1 ✅ |
| 24 | `20_code/config/20260328-24-create-fn-cleanup-token-scaduti-mctit.yaml` | Pulizia periodica token scaduti/utilizzati | 1 ✅ |
| 25 | `20_code/script/20260328-25-create-fn-check-operatore-invitabile-mctit.yaml` | Check invitabilita' operatore | 3 ✅ |
| 26 | `20_code/script/20260328-26-update-fn-get-user-profile-auth-flags-mctit.yaml` | +`deve_cambiare_password` nel profilo | 1 ✅ |

> **Nota**: la migration -26 aggiunge solo `deve_cambiare_password`. Le chiavi
> `totp_abilitato` e `totp_obbligatorio` saranno aggiunte con una nuova migration
> in Fase 4, quando la tabella `auth_totp_device` e' in uso.

### Altro (20_code)

| # | File | Oggetto | Fase |
| --- | --- | --- | --- |
| 02 | `20_code/script/20260328-02-update-trgfn-lock-columns-guc-override-mctit.yaml` | GUC override per `trgfn_lock_columns` | infra ✅ |

### Seed dati (80_data)

| # | File | Oggetto | Fase |
| --- | --- | --- | --- |
| 60 | `80_data/changelog/20260329-60-upsert-config-email-account-mctit.yaml` | Account SISTEMA (placeholder SMTP) | 1 ✅ |
| 61 | `80_data/changelog/20260329-61-upsert-config-email-template-mctit.yaml` | 4 template base (invito, reset, conferma, generico) | 1 ✅ |
| — | `80_data/sql/config/email_account.csv` | CSV seed account | 1 ✅ |
| — | `80_data/sql/config/email_template.csv` | CSV seed template | 1 ✅ |

### Riepilogo totale

- **7 tabelle nuove**: email_account, email_template, email_log, email_outbox, email_allegato, token_monouso, auth_totp_device
- **3 ALTER** su risorse_umane_auth_user: +3 colonne (deve_cambiare_password, invito_inviato_at, totp_obbligatorio)
- **5 funzioni**: fn_resolve_email_account, fn_resolve_email_template, fn_cleanup_token_scaduti, fn_check_operatore_invitabile, fn_get_user_profile (update)
- **1 infrastruttura**: GUC override per lock columns
- **2 seed** con CSV: 1 account SISTEMA + 4 template base

### Da fare in Fase 4 (DB)

| Cosa | Dettaglio |
| --- | --- |
| Update `fn_get_user_profile` | Aggiungere `totp_abilitato` (lookup su `auth_totp_device`) e `totp_obbligatorio` al JSONB |

### Migliorie rispetto al piano originale

Migliorie introdotte durante la creazione DB (non presenti nel piano iniziale del 2026-03-28):

| Miglioria | Descrizione | Impatto backend |
| --- | --- | --- |
| `email_outbox` | Tabella bozze editabili (DRAFT→READY→SENT→CANCELLED) | Nuovo service `EmailOutboxService` |
| `email_allegato` | Allegati per outbox e log (UPLOAD/TEMPLATE) | Gestione file storage + MIME |
| `tipo_prestazione_id` su template | Specializzazione per tipo pratica | Fallback 5 livelli invece di 3 |
| `ambito` su log/outbox | SISTEMA/REPARTO/OPERATORE per visibilita' | Filtro per ruolo nelle API |
| `pratica_id` su log/outbox | Collegamento a pratiche | Tab comunicazioni nel drawer pratica |
| `destinatari_cc` su log/outbox | Array CC | Supporto CC nelle email |
| `corpo_inviato_html/testo` su log | Corpo esattamente come inviato | Consultazione fedele post-invio |
| `email_outbox_id` su log | FK circolare outbox↔log | Tracciabilita' bozza→invio |
| GUC override lock columns | `zeroerp.allow_lock_columns_override` | Per manutenzione colonne protette |
