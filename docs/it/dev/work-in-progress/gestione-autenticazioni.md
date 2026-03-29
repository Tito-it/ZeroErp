# Gestione Autenticazioni — WIP

> Documento di pianificazione per il completamento del sistema di autenticazione.
> Data inizio: 2026-03-28
> Stato: **PIANIFICAZIONE**
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

### Infrastruttura

- [ ] PRE-1 — Server SMTP disponibile (o servizio: SendGrid, Mailgun, Amazon SES)
- [ ] PRE-2 — Decisione su servizio email: SMTP aziendale vs servizio cloud
- [ ] PRE-3 — Dominio email verificato per invio (es. `@azienda.it`)

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

- [ ] 1.1.1 — Creare tabella `config.email_account`

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

- [ ] 1.1.2 — Creare tabella `config.email_template`

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

- [ ] 1.1.3 — Creare tabella `config.email_log`

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

- [ ] 1.1.4 — Creare tabella `config.email_outbox`

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

- [ ] 1.1.5 — Creare tabella `config.email_allegato`

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

- [ ] 1.1.6 — Aggiornare tabella `config.email_log` — colonne corpo inviato

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

- [ ] 1.1.7 — Seed dati: account di sistema (codice `SISTEMA`) e template base
  - Template `INVITO_OPERATORE`
  - Template `RESET_PASSWORD`
  - Template `CAMBIO_PASSWORD_CONFERMA`
  - Template `NOTIFICA_GENERICA`

#### Backend

- [ ] 1.1.8 — Creare `apps/core/services/email_service.py` — `EmailDispatchService`

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

- [ ] 1.1.9 — Creare `apps/core/services/email_outbox_service.py` — `EmailOutboxService`

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

- [ ] 1.1.10 — Creare `apps/core/db/email_repository.py`

Responsabilità:
  - Query su `config.email_account`, `config.email_template`, `config.email_log`
  - Query su `config.email_outbox`, `config.email_allegato`
  - Decriptazione password SMTP (usando `django.core.signing` o `Fernet`)
  - Insert/update `email_log`, `email_outbox`, `email_allegato`

- [ ] 1.1.11 — Creare management command `send_pending_emails`
  - Processa email con stato `PENDING` o `RETRY`
  - Eseguibile come cron job (pgAgent o crontab)
  - Flag `--dry-run` per preview

- [ ] 1.1.12 — Configurare `EMAIL_BACKEND` in settings.py
  - Default: `django.core.mail.backends.smtp.EmailBackend`
  - Dev/test: `django.core.mail.backends.console.EmailBackend`
  - Il service NON usa il backend globale Django ma connessioni SMTP per-account
  - Configurazione storage allegati: `EMAIL_ATTACHMENTS_ROOT`, `EMAIL_ATTACHMENT_MAX_SIZE_MB`

- [ ] 1.1.13 — API admin per gestione account email (CRUD)
  - `GET/POST /api/v1/amm-software/email-accounts/`
  - `GET/PUT/DELETE /api/v1/amm-software/email-accounts/<id>/`
  - Solo ruolo ADMIN
  - La password SMTP viene accettata in chiaro e salvata crittografata

- [ ] 1.1.14 — API admin per gestione template email (CRUD)
  - `GET/POST /api/v1/amm-software/email-templates/`
  - `GET/PUT/DELETE /api/v1/amm-software/email-templates/<id>/`
  - Solo ruolo ADMIN
  - Endpoint preview: `POST .../preview/` con variabili di esempio

- [ ] 1.1.15 — API outbox email (preparazione, modifica, invio bozze)
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

- [ ] 1.1.16 — API allegati email
  - `POST /api/v1/email/outbox/<id>/allegati/` — upload allegato (multipart)
  - `GET /api/v1/email/outbox/<id>/allegati/` — lista allegati della bozza
  - `DELETE /api/v1/email/allegati/<allegato_id>/` — rimuovi allegato
  - `GET /api/v1/email/allegati/<allegato_id>/download/` — download file
  - Validazione: tipo MIME whitelist, dimensione max, numero max allegati per email
  - Stesso endpoint download usabile per allegati da `email_log` (consultazione storica)

- [ ] 1.1.17 — API consultazione log email (migliorata, con visibilita' per ambito)
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

- [ ] 1.1.18 — Pannello admin: gestione account email
  - Lista account con stato attivo/inattivo
  - Form creazione/modifica con test connessione SMTP
  - Associazione a reparto (autocomplete unità organizzativa)

- [ ] 1.1.19 — Pannello admin: gestione template email
  - Lista template raggruppati per codice
  - Editor con preview HTML
  - Indicazione variabili disponibili per tipo template

- [ ] 1.1.20 — Dialog/drawer "Componi email" (componente riutilizzabile)

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

- [ ] 1.1.21 — Consultazione log email (con visibilita' per ambito)
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

- [ ] 1.1.22 — Tab "Comunicazioni" nel drawer pratica
  - Lista email inviate nel contesto della pratica (`pratica_id`)
  - Ordinate per data, con stato e destinatario
  - Click → apre dettaglio email (corpo inviato + allegati)
  - Pulsante "Nuova comunicazione" → apre dialog Componi email (1.1.20)
    con `pratica_id` pre-impostato, template risolto per tipo pratica + reparto

#### Test

- [ ] 1.1.T1 — Test Django: `EmailDispatchService` con mock SMTP
- [ ] 1.1.T2 — Test Django: risoluzione account per reparto con fallback
- [ ] 1.1.T3 — Test Django: risoluzione template per reparto+lingua con fallback
- [ ] 1.1.T4 — Test Django: rendering template con variabili
- [ ] 1.1.T5 — Test Django: retry email fallite
- [ ] 1.1.T6 — Test Django: `EmailOutboxService.prepare_draft` → bozza creata con corpo renderizzato
- [ ] 1.1.T7 — Test Django: modifica bozza (oggetto, corpo, CC) → campi aggiornati
- [ ] 1.1.T8 — Test Django: conferma e invio bozza → stato SENT + email_log creato con corpo inviato
- [ ] 1.1.T9 — Test Django: annullamento bozza → stato CANCELLED + allegati eliminati
- [ ] 1.1.T10 — Test Django: upload allegato → file salvato + record creato
- [ ] 1.1.T11 — Test Django: validazione allegato (tipo MIME non consentito, dimensione eccessiva → errore)
- [ ] 1.1.T12 — Test Django: invio con allegati → email contiene attachment MIME
- [ ] 1.1.T13 — Test Django: re-invio da log → nuova bozza pre-compilata con corpo/allegati originali
- [ ] 1.1.T14 — Test Django: consultazione log con corpo inviato fedele (non ri-renderizzato)

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

- [ ] 1.2.1 — Creare tabella `config.token_monouso`

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

- [ ] 1.2.2 — Creare funzione `config.fn_cleanup_token_scaduti()`
  - Elimina token scaduti o utilizzati da più di N giorni (configurabile)
  - Eseguibile come job pgAgent periodico

#### Backend

- [ ] 1.2.3 — Creare `apps/core/services/token_service.py` — `TokenService`

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

- [ ] 1.2.4 — Creare `apps/core/db/token_repository.py`
  - Query su `config.token_monouso`
  - Insert, update stato, cleanup

#### Test

- [ ] 1.2.T1 — Test Django: creazione token + validazione
- [ ] 1.2.T2 — Test Django: token scaduto → rifiutato
- [ ] 1.2.T3 — Test Django: token già utilizzato → rifiutato
- [ ] 1.2.T4 — Test Django: invalidazione token precedenti dello stesso tipo

---

### 1.3 BB-3: Cambio Password Obbligatorio

#### Concetto

Quando un operatore deve cambiare la password (primo accesso, reset admin, scadenza policy),
il login restituisce un flag `password_change_required: true`. Il frontend blocca la navigazione
e mostra la pagina di cambio password.

#### DB

- [ ] 1.3.1 — Aggiungere colonna a `anagrafiche.risorse_umane_auth_user`:

```sql
ALTER TABLE anagrafiche.risorse_umane_auth_user
  ADD COLUMN deve_cambiare_password BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN anagrafiche.risorse_umane_auth_user.deve_cambiare_password
  IS 'Se true, l''operatore deve cambiare password al prossimo login';
```

- [ ] 1.3.2 — Aggiornare `script.fn_get_user_profile()`:
  - Includere `deve_cambiare_password` nel JSONB di risposta sotto `utente`

#### Backend

- [ ] 1.3.3 — Modificare `AuditTokenObtainPairView` (auth_views.py):
  - Dopo login riuscito, leggere `deve_cambiare_password`
  - Se `true` → aggiungere al response JSON: `password_change_required: true`
  - Il token viene comunque rilasciato (serve per chiamare l'endpoint cambio password)

- [ ] 1.3.4 — Creare endpoint `POST /api/v1/auth/change-password/`
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

- [ ] 1.3.5 — Creare middleware/permission per blocco navigazione
  - Se `deve_cambiare_password = true`, gli unici endpoint consentiti sono:
    - `POST /api/v1/auth/change-password/`
    - `POST /api/v1/auth/logout/`
    - `GET /api/v1/core/me/`
  - Tutti gli altri → HTTP 403 con codice `E_CAMBIO_PASSWORD_RICHIESTO`

#### Frontend

- [ ] 1.3.6 — Creare pagina `ChangePasswordView.vue`
  - Route: `/change-password` (pubblica per utenti autenticati)
  - Form: password attuale, nuova password, conferma nuova password
  - Indicatore forza password in tempo reale
  - Validazione client-side (lunghezza minima, match conferma)
  - Al successo: aggiorna token nello store e redirect a home

- [ ] 1.3.7 — Modificare `auth.js` store:
  - Salvare `passwordChangeRequired` dallo stato login
  - Getter `mustChangePassword`

- [ ] 1.3.8 — Modificare route guard (router/index.js):
  - Se `mustChangePassword === true` → redirect forzato a `/change-password`
  - Bloccare navigazione a qualsiasi altra rotta

- [ ] 1.3.9 — Aggiungere link "Cambia password" nel menu profilo utente
  - Accessibile sempre (non solo quando obbligatorio)

#### Test

- [ ] 1.3.T1 — Test Django: login con `deve_cambiare_password=true` → flag nel response
- [ ] 1.3.T2 — Test Django: cambio password con validazioni
- [ ] 1.3.T3 — Test Django: middleware blocca navigazione se flag attivo
- [ ] 1.3.T4 — Test Django: dopo cambio password, flag resettato

---

## Fase 2 — Reset Password Dimenticata

> **Obiettivo**: permettere all'operatore di resettare la password via email,
> senza intervento admin.
> **Dipende da**: BB-1 (email), BB-2 (token monouso), BB-3 (cambio password)

### DB

- [ ] 2.1 — Nessuna modifica DB aggiuntiva
  - Usa `config.token_monouso` con tipo `RESET_PASSWORD`
  - Usa `config.email_template` con codice `RESET_PASSWORD`

### Backend

- [ ] 2.2 — Creare endpoint `POST /api/v1/auth/password-reset-request/`
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

- [ ] 2.3 — Creare endpoint `POST /api/v1/auth/password-reset-confirm/`
  - Input: `{ token, new_password, new_password_confirm }`
  - **Non autenticato**
  - Logica:
    1. `TokenService.consume(token, 'RESET_PASSWORD', ip=request_ip)`
    2. Se valido → `user.set_password(new_password)`, reset flag `deve_cambiare_password`
    3. Blacklist tutti i refresh token dell'utente
    4. Invia email conferma con template `CAMBIO_PASSWORD_CONFERMA`
    5. Log audit: `PASSWORD_RESET`
  - Response: `{ message: "Password aggiornata" }` (senza token — deve ri-loggarsi)

- [ ] 2.4 — Creare endpoint `GET /api/v1/auth/password-reset-validate/{token}/`
  - **Non autenticato**
  - Verifica se il token è ancora valido (senza consumarlo)
  - Usato dal frontend per mostrare il form o un messaggio di errore/scadenza

### Frontend

- [ ] 2.5 — Aggiungere link "Password dimenticata?" nella `LoginView.vue`

- [ ] 2.6 — Creare pagina `PasswordResetRequestView.vue`
  - Route: `/password-reset` (pubblica)
  - Form: solo campo email
  - Messaggio di conferma generico (non rivela se email esiste)

- [ ] 2.7 — Creare pagina `PasswordResetConfirmView.vue`
  - Route: `/reset-password/:token` (pubblica)
  - All'apertura: chiama endpoint validate per verificare token
  - Se token valido → form nuova password + conferma
  - Se token invalido/scaduto → messaggio errore + link a nuova richiesta
  - Al successo → redirect a login con messaggio

### Test

- [ ] 2.T1 — Test Django: richiesta reset con email esistente → token creato + email accodata
- [ ] 2.T2 — Test Django: richiesta reset con email inesistente → 200 (nessun token)
- [ ] 2.T3 — Test Django: conferma reset con token valido → password cambiata
- [ ] 2.T4 — Test Django: conferma reset con token scaduto → errore
- [ ] 2.T5 — Test Django: rate limiting richieste reset

---

## Fase 3 — Invito Operatore al Primo Accesso

> **Obiettivo**: quando l'admin abilita un operatore, il sistema invia
> automaticamente un'email di invito con link di attivazione.
> **Dipende da**: BB-1 (email), BB-2 (token), BB-3 (cambio password), Fase 2

### DB

- [ ] 3.1 — Aggiungere colonna a `anagrafiche.risorse_umane_auth_user`:

```sql
ALTER TABLE anagrafiche.risorse_umane_auth_user
  ADD COLUMN invito_inviato_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN anagrafiche.risorse_umane_auth_user.invito_inviato_at
  IS 'Timestamp ultimo invito inviato all''operatore (NULL = mai invitato)';
```

- [ ] 3.2 — Creare funzione `anagrafiche.fn_check_operatore_invitabile(p_auth_user_id)`
  - Verifica: utente esiste, è attivo, ha email, non ha mai effettuato login
  - Ritorna JSONB con `{invitabile: bool, motivo: text, email: text}`

### Backend

- [ ] 3.3 — Creare `apps/anagrafiche/services/invito_operatore_service.py`

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

- [ ] 3.4 — Creare endpoint admin `POST /api/v1/amm-software/operatori/<id>/invita/`
  - Solo ruolo ADMIN
  - Chiama `invito_operatore_service.prepara_invito()`
  - Response: `{ outbox_id: 123, email: "m***@azienda.it" }` (bozza pronta per anteprima)
  - Il frontend apre il dialog "Componi email" (1.1.20) con la bozza editabile
  - L'invio effettivo avviene quando l'admin conferma dal dialog

- [ ] 3.5 — Creare endpoint admin `POST /api/v1/amm-software/operatori/<id>/reinvia-invito/`
  - Solo ruolo ADMIN
  - Per rinviare invito scaduto o non ricevuto
  - Stessa logica: prepara bozza → anteprima → conferma

- [ ] 3.6 — Creare endpoint pubblico `POST /api/v1/auth/attivazione/`
  - Input: `{ token, new_password, new_password_confirm }`
  - Logica:
    1. `TokenService.consume(token, 'INVITO_OPERATORE')`
    2. `user.set_password(new_password)` con validazione
    3. Reset `deve_cambiare_password = false`
    4. Log audit: `ACCOUNT_ATTIVATO`
  - Response: `{ message: "Account attivato" }` (deve ri-loggarsi)

- [ ] 3.7 — Opzionale: trigger automatico invio invito
  - Quando admin imposta `is_active = true` su un operatore mai loggato
  - Via signal Django o hook nel service di abilitazione esistente

### Frontend

- [ ] 3.8 — Creare pagina `AttivazioneView.vue`
  - Route: `/attivazione/:token` (pubblica)
  - Valida token all'apertura
  - Form: nuova password + conferma
  - Messaggio benvenuto personalizzato
  - Al successo → redirect a login

- [ ] 3.9 — Aggiungere bottoni nel drawer operatore (amm-software):
  - "Invia invito" (se mai invitato e attivo)
  - "Reinvia invito" (se già invitato)
  - Badge: "Invitato il DD/MM/YYYY" o "Mai invitato"

- [ ] 3.10 — Colonna "Stato invito" nella lista operatori
  - Mai invitato / Invitato (data) / Attivato

### Test

- [ ] 3.T1 — Test Django: invio invito → token + email + flag
- [ ] 3.T2 — Test Django: attivazione con token valido → password impostata
- [ ] 3.T3 — Test Django: reinvio invalida token precedente
- [ ] 3.T4 — Test Django: invito a operatore non invitabile → errore

---

## Fase 4 — Autenticazione a Due Fattori (2FA TOTP)

> **Obiettivo**: aggiungere autenticazione TOTP opzionale (Google Authenticator, Authy).
> **Dipende da**: Fasi 1-3 completate
> **Nuove dipendenze Python**: `pyotp`, `qrcode`, `Pillow`

### DB

- [ ] 4.1 — Creare tabella `config.auth_totp_device`

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

- [ ] 4.2 — Aggiungere colonna a `anagrafiche.risorse_umane_auth_user`:

```sql
ALTER TABLE anagrafiche.risorse_umane_auth_user
  ADD COLUMN totp_obbligatorio BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN anagrafiche.risorse_umane_auth_user.totp_obbligatorio
  IS 'Se true, l''operatore DEVE configurare il 2FA per accedere';
```

- [ ] 4.3 — Aggiornare `script.fn_get_user_profile()`:
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

## Appendice A — Specifiche DB Complete

> Questa appendice contiene le DDL, funzioni e seed da creare sul **server DB**.
> Percorso base: `db/changelog/migrations_v2/`
>
> **ATTENZIONE — Progressivi aggiornati**: le sezioni A.1.1-A.1.7 e A.1.8-A.1.10
> sono state scritte con progressivi provvisori (`-01` a `-10`). I file **effettivamente
> creati** nel repo usano i progressivi `-13` a `-19` (vedi riepilogo A.4).
> Le DDL qui sotto restano valide come **riferimento strutturale** — il contenuto
> SQL e' quello implementato nei changeset reali.
> Per i progressivi di funzioni e seed si usera' `-22` in avanti (vedi A.4).

---

## A.1 Tabelle (00_schema)

### A.1.1 `config.email_account`

**File**: `00_schema/config/20260328-01-create-email-account-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Account email per invio notifiche.
# Ogni unita' organizzativa puo' avere il proprio account SMTP.
# Account con unita_organizzativa_id NULL = account di sistema (fallback).
# Fase: 1 (BB-1 Sistema Email Generico)
# ------------------------------------------------------------

databaseChangeLog:
  - logicalFilePath: migrations_v2/00_schema/config/20260328-01-create-email-account-mctit.yaml

  - changeSet:
      id: 20260328-01-create-email-account
      author: mctit
      comment: >
        Account SMTP per invio email.
        Ogni unita' organizzativa puo' avere il proprio account.
        Account con unita_organizzativa_id NULL = account di sistema/fallback.
        La password SMTP e' salvata crittografata (Fernet lato Django).
      changes:
        - createTable:
            schemaName: config
            tableName: email_account
            remarks: "Account SMTP per invio email, associabili a unita' organizzativa."
            columns:
              - column:
                  name: id
                  type: integer
                  autoIncrement: true
                  generationType: BY DEFAULT
                  remarks: "PK tecnica."
                  constraints:
                    primaryKey: true
                    primaryKeyName: pk_email_account
                    nullable: false

              - column:
                  name: codice
                  type: character varying(50)
                  remarks: "Codice univoco account (es. SISTEMA, ACQ_01)."
                  constraints:
                    nullable: false

              - column:
                  name: descrizione
                  type: text
                  remarks: "Descrizione leggibile (es. 'Account di sistema', 'Ufficio Acquisti')."
                  constraints:
                    nullable: false

              - column:
                  name: unita_organizzativa_id
                  type: integer
                  remarks: "FK reparto proprietario. NULL = account di sistema/fallback."
                  constraints:
                    nullable: true

              - column:
                  name: smtp_host
                  type: character varying(255)
                  remarks: "Hostname server SMTP (es. smtp.gmail.com)."
                  constraints:
                    nullable: false

              - column:
                  name: smtp_port
                  type: integer
                  defaultValueNumeric: 587
                  remarks: "Porta SMTP (587=STARTTLS, 465=SSL, 25=plain)."
                  constraints:
                    nullable: false

              - column:
                  name: smtp_use_tls
                  type: boolean
                  defaultValueBoolean: true
                  remarks: "Abilita STARTTLS."
                  constraints:
                    nullable: false

              - column:
                  name: smtp_use_ssl
                  type: boolean
                  defaultValueBoolean: false
                  remarks: "Abilita SSL diretto (porta 465). Mutuamente esclusivo con smtp_use_tls."
                  constraints:
                    nullable: false

              - column:
                  name: smtp_username
                  type: character varying(255)
                  remarks: "Username autenticazione SMTP."
                  constraints:
                    nullable: false

              - column:
                  name: smtp_password_encrypted
                  type: character varying(512)
                  remarks: "Password SMTP crittografata con Fernet (chiave derivata da Django SECRET_KEY). MAI salvare in chiaro."
                  constraints:
                    nullable: false

              - column:
                  name: email_from
                  type: character varying(255)
                  remarks: "Indirizzo mittente completo (es. 'Ufficio Acquisti <acquisti@azienda.it>')."
                  constraints:
                    nullable: false

              - column:
                  name: email_reply_to
                  type: character varying(255)
                  remarks: "Indirizzo reply-to opzionale."
                  constraints:
                    nullable: true

              - column:
                  name: attivo
                  type: boolean
                  defaultValueBoolean: true
                  constraints:
                    nullable: false

              - column:
                  name: meta
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  constraints:
                    nullable: false

              - column:
                  name: data_insert
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_insert
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

              - column:
                  name: data_update
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_update
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

        - addUniqueConstraint:
            schemaName: config
            tableName: email_account
            columnNames: codice
            constraintName: uq_email_account_codice

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_account
            baseColumnNames: unita_organizzativa_id
            referencedTableSchemaName: config
            referencedTableName: unita_organizzative
            referencedColumnNames: id
            constraintName: fk_email_account_unita_organizzativa
            onUpdate: NO ACTION
            onDelete: RESTRICT

        - sql:
            sql: |
              ALTER TABLE config.email_account
                ADD CONSTRAINT chk_email_account_smtp_port
                CHECK (smtp_port BETWEEN 1 AND 65535);

              ALTER TABLE config.email_account
                ADD CONSTRAINT chk_email_account_tls_ssl_exclusive
                CHECK (NOT (smtp_use_tls AND smtp_use_ssl));

              COMMENT ON TABLE config.email_account
                IS 'Account SMTP per invio email. Ogni reparto puo'' avere il proprio. NULL su unita_organizzativa_id = account di sistema/fallback.';

      rollback:
        - dropTable:
            schemaName: config
            tableName: email_account
```

---

### A.1.2 `config.email_template`

**File**: `00_schema/config/20260328-02-create-email-template-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Template email parametrizzabili con variabili {{...}}.
# Override per unita' organizzativa e lingua.
# Fase: 1 (BB-1 Sistema Email Generico)
# ------------------------------------------------------------

databaseChangeLog:
  - logicalFilePath: migrations_v2/00_schema/config/20260328-02-create-email-template-mctit.yaml

  - changeSet:
      id: 20260328-02-create-email-template
      author: mctit
      comment: >
        Template email con supporto variabili {{...}}.
        Override per reparto (unita_organizzativa_id) e lingua.
        Template con unita_organizzativa_id NULL = default di sistema.
      changes:
        - createTable:
            schemaName: config
            tableName: email_template
            remarks: "Template email parametrizzabili, override per reparto e lingua."
            columns:
              - column:
                  name: id
                  type: integer
                  autoIncrement: true
                  generationType: BY DEFAULT
                  remarks: "PK tecnica."
                  constraints:
                    primaryKey: true
                    primaryKeyName: pk_email_template
                    nullable: false

              - column:
                  name: codice
                  type: character varying(100)
                  remarks: "Codice tipo template (es. INVITO_OPERATORE, RESET_PASSWORD)."
                  constraints:
                    nullable: false

              - column:
                  name: unita_organizzativa_id
                  type: integer
                  remarks: "FK reparto per override. NULL = template di sistema/default."
                  constraints:
                    nullable: true

              - column:
                  name: tipo_prestazione_id
                  type: integer
                  remarks: "FK tipo prestazione per specializzazione. NULL = generico."
                  constraints:
                    nullable: true

              - column:
                  name: lingua
                  type: character varying(5)
                  defaultValue: "it"
                  remarks: "Codice lingua ISO (es. it, en, de)."
                  constraints:
                    nullable: false

              - column:
                  name: oggetto
                  type: text
                  remarks: "Oggetto email con variabili {{...}} (es. 'Benvenuto {{nome}}')."
                  constraints:
                    nullable: false

              - column:
                  name: corpo_html
                  type: text
                  remarks: "Corpo email HTML con variabili {{...}}."
                  constraints:
                    nullable: false

              - column:
                  name: corpo_testo
                  type: text
                  remarks: "Corpo email plaintext (fallback). Se NULL, generato da corpo_html."
                  constraints:
                    nullable: true

              - column:
                  name: variabili_disponibili
                  type: jsonb
                  defaultValueComputed: "'[]'::jsonb"
                  remarks: "Array JSON dei nomi variabili accettate (es. ['nome','link','azienda']). Documentativo per UI admin."
                  constraints:
                    nullable: false

              - column:
                  name: attivo
                  type: boolean
                  defaultValueBoolean: true
                  constraints:
                    nullable: false

              - column:
                  name: meta
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  constraints:
                    nullable: false

              - column:
                  name: data_insert
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_insert
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

              - column:
                  name: data_update
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_update
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

        - addUniqueConstraint:
            schemaName: config
            tableName: email_template
            columnNames: codice, unita_organizzativa_id, tipo_prestazione_id, lingua
            constraintName: uq_email_template_codice_uo_tp_lingua

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_template
            baseColumnNames: unita_organizzativa_id
            referencedTableSchemaName: config
            referencedTableName: unita_organizzative
            referencedColumnNames: id
            constraintName: fk_email_template_unita_organizzativa
            onUpdate: NO ACTION
            onDelete: RESTRICT

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_template
            baseColumnNames: tipo_prestazione_id
            referencedTableSchemaName: pratiche
            referencedTableName: tipi_prestazione
            referencedColumnNames: id
            constraintName: fk_email_template_tipo_pratica
            onUpdate: NO ACTION
            onDelete: RESTRICT

      rollback:
        - dropTable:
            schemaName: config
            tableName: email_template
```

---

### A.1.3 `config.email_log`

**File**: `00_schema/config/20260328-03-create-email-log-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Log invio email con gestione retry.
# Fase: 1 (BB-1 Sistema Email Generico)
# ------------------------------------------------------------

databaseChangeLog:
  - logicalFilePath: migrations_v2/00_schema/config/20260328-03-create-email-log-mctit.yaml

  - changeSet:
      id: 20260328-03-create-email-log
      author: mctit
      comment: >
        Log di tutti gli invii email con stato, retry e tracciabilita'.
        Supporta coda asincrona: stato PENDING -> SENT/FAILED -> RETRY.
      changes:
        - createTable:
            schemaName: config
            tableName: email_log
            remarks: "Log invio email con gestione retry e tracciabilita'."
            columns:
              - column:
                  name: id
                  type: bigint
                  autoIncrement: true
                  generationType: BY DEFAULT
                  remarks: "PK tecnica."
                  constraints:
                    primaryKey: true
                    primaryKeyName: pk_email_log
                    nullable: false

              - column:
                  name: email_account_id
                  type: integer
                  remarks: "FK account SMTP usato per l'invio."
                  constraints:
                    nullable: true

              - column:
                  name: email_template_id
                  type: integer
                  remarks: "FK template usato (NULL se email composta manualmente)."
                  constraints:
                    nullable: true

              - column:
                  name: destinatario
                  type: character varying(255)
                  remarks: "Indirizzo email destinatario."
                  constraints:
                    nullable: false

              - column:
                  name: oggetto
                  type: text
                  remarks: "Oggetto email renderizzato."
                  constraints:
                    nullable: false

              - column:
                  name: stato
                  type: character varying(20)
                  defaultValue: "PENDING"
                  remarks: "Stato invio: PENDING, SENT, FAILED, RETRY."
                  constraints:
                    nullable: false

              - column:
                  name: errore
                  type: text
                  remarks: "Dettaglio errore ultimo tentativo (NULL se successo)."
                  constraints:
                    nullable: true

              - column:
                  name: tentativi
                  type: integer
                  defaultValueNumeric: 0
                  remarks: "Numero tentativi effettuati."
                  constraints:
                    nullable: false

              - column:
                  name: max_tentativi
                  type: integer
                  defaultValueNumeric: 3
                  remarks: "Numero massimo tentativi consentiti."
                  constraints:
                    nullable: false

              - column:
                  name: prossimo_tentativo
                  type: timestamp with time zone
                  remarks: "Timestamp prossimo tentativo schedulato (per retry)."
                  constraints:
                    nullable: true

              - column:
                  name: inviato_at
                  type: timestamp with time zone
                  remarks: "Timestamp invio riuscito."
                  constraints:
                    nullable: true

              - column:
                  name: contesto_json
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  remarks: "Variabili usate per il rendering del template."
                  constraints:
                    nullable: false

              - column:
                  name: auth_user_id
                  type: integer
                  remarks: "FK operatore destinatario (se applicabile)."
                  constraints:
                    nullable: true

              - column:
                  name: tx_id
                  type: uuid
                  remarks: "Transaction ID per correlazione audit."
                  constraints:
                    nullable: true

              - column:
                  name: data_insert
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_insert
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_log
            baseColumnNames: email_account_id
            referencedTableSchemaName: config
            referencedTableName: email_account
            referencedColumnNames: id
            constraintName: fk_email_log_email_account
            onUpdate: NO ACTION
            onDelete: SET NULL

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_log
            baseColumnNames: email_template_id
            referencedTableSchemaName: config
            referencedTableName: email_template
            referencedColumnNames: id
            constraintName: fk_email_log_email_template
            onUpdate: NO ACTION
            onDelete: SET NULL

        - createIndex:
            schemaName: config
            tableName: email_log
            indexName: ix_email_log_stato_prossimo_tentativo
            columns:
              - column:
                  name: stato
              - column:
                  name: prossimo_tentativo

        - createIndex:
            schemaName: config
            tableName: email_log
            indexName: ix_email_log_auth_user_id
            columns:
              - column:
                  name: auth_user_id

        - sql:
            sql: |
              ALTER TABLE config.email_log
                ADD CONSTRAINT chk_email_log_stato
                CHECK (stato IN ('PENDING', 'SENT', 'FAILED', 'RETRY'));

      rollback:
        - dropTable:
            schemaName: config
            tableName: email_log
```

---

### A.1.4 `config.token_monouso`

**File**: `00_schema/config/20260328-04-create-token-monouso-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Token monouso generico: invito, reset password, conferme.
# Il token in chiaro NON viene salvato, solo l'hash SHA-256.
# Fase: 1 (BB-2 Token Monouso Generico)
# ------------------------------------------------------------

databaseChangeLog:
  - logicalFilePath: migrations_v2/00_schema/config/20260328-04-create-token-monouso-mctit.yaml

  - changeSet:
      id: 20260328-04-create-token-monouso
      author: mctit
      comment: >
        Token monouso generico riutilizzabile per inviti, reset password,
        conferme email, attivazione account. Il token in chiaro non viene
        mai salvato in DB, solo l'hash SHA-256. Supporta scadenza e
        tracciamento IP di utilizzo.
      changes:
        - createTable:
            schemaName: config
            tableName: token_monouso
            remarks: "Token monouso generico con hash, scadenza e tracciamento utilizzo."
            columns:
              - column:
                  name: id
                  type: bigint
                  autoIncrement: true
                  generationType: BY DEFAULT
                  remarks: "PK tecnica."
                  constraints:
                    primaryKey: true
                    primaryKeyName: pk_token_monouso
                    nullable: false

              - column:
                  name: token_hash
                  type: character varying(128)
                  remarks: "SHA-256 del token. Il token in chiaro NON viene salvato."
                  constraints:
                    nullable: false

              - column:
                  name: tipo
                  type: character varying(50)
                  remarks: "Tipo token: INVITO_OPERATORE, RESET_PASSWORD, CONFERMA_EMAIL, ecc."
                  constraints:
                    nullable: false

              - column:
                  name: auth_user_id
                  type: integer
                  remarks: "FK utente Django associato al token."
                  constraints:
                    nullable: false

              - column:
                  name: scadenza
                  type: timestamp with time zone
                  remarks: "Timestamp scadenza token."
                  constraints:
                    nullable: false

              - column:
                  name: utilizzato
                  type: boolean
                  defaultValueBoolean: false
                  remarks: "Flag: true se il token e' stato consumato."
                  constraints:
                    nullable: false

              - column:
                  name: utilizzato_at
                  type: timestamp with time zone
                  remarks: "Timestamp consumo token."
                  constraints:
                    nullable: true

              - column:
                  name: ip_utilizzo
                  type: inet
                  remarks: "IP da cui il token e' stato consumato."
                  constraints:
                    nullable: true

              - column:
                  name: meta
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  remarks: "Metadati aggiuntivi (es. invitato_da, contesto)."
                  constraints:
                    nullable: false

              - column:
                  name: data_insert
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_insert
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

        - addUniqueConstraint:
            schemaName: config
            tableName: token_monouso
            columnNames: token_hash
            constraintName: uq_token_monouso_token_hash

        - createIndex:
            schemaName: config
            tableName: token_monouso
            indexName: ix_token_monouso_tipo_user_utilizzato
            columns:
              - column:
                  name: tipo
              - column:
                  name: auth_user_id
              - column:
                  name: utilizzato

        - createIndex:
            schemaName: config
            tableName: token_monouso
            indexName: ix_token_monouso_scadenza
            columns:
              - column:
                  name: scadenza

      rollback:
        - dropTable:
            schemaName: config
            tableName: token_monouso
```

---

### A.1.5 `config.auth_totp_device` (Fase 4)

**File**: `00_schema/config/20260328-05-create-auth-totp-device-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Device TOTP per autenticazione a due fattori.
# 1:1 con auth_user. Secret crittografato con Fernet.
# Fase: 4 (2FA TOTP)
# ------------------------------------------------------------

databaseChangeLog:
  - logicalFilePath: migrations_v2/00_schema/config/20260328-05-create-auth-totp-device-mctit.yaml

  - changeSet:
      id: 20260328-05-create-auth-totp-device
      author: mctit
      comment: >
        Device TOTP per 2FA. Relazione 1:1 con auth_user.
        Secret crittografato con Fernet (chiave derivata da Django SECRET_KEY).
        Recovery codes salvati come array di hash SHA-256.
        Anti-replay: ultimo codice usato salvato per evitare riutilizzo.
      changes:
        - createTable:
            schemaName: config
            tableName: auth_totp_device
            remarks: "Device TOTP per autenticazione a due fattori, 1:1 con auth_user."
            columns:
              - column:
                  name: id
                  type: bigint
                  autoIncrement: true
                  generationType: BY DEFAULT
                  remarks: "PK tecnica."
                  constraints:
                    primaryKey: true
                    primaryKeyName: pk_auth_totp_device
                    nullable: false

              - column:
                  name: auth_user_id
                  type: integer
                  remarks: "FK auth_user. 1:1 — un solo device TOTP per utente."
                  constraints:
                    nullable: false

              - column:
                  name: secret_encrypted
                  type: character varying(512)
                  remarks: "Secret TOTP crittografato con Fernet. MAI salvare in chiaro."
                  constraints:
                    nullable: false

              - column:
                  name: abilitato
                  type: boolean
                  defaultValueBoolean: false
                  remarks: "Device abilitato per il login."
                  constraints:
                    nullable: false

              - column:
                  name: confermato
                  type: boolean
                  defaultValueBoolean: false
                  remarks: "true solo dopo prima verifica riuscita durante il setup."
                  constraints:
                    nullable: false

              - column:
                  name: recovery_codes_hash
                  type: jsonb
                  defaultValueComputed: "'[]'::jsonb"
                  remarks: "Array JSON di hash SHA-256 dei recovery codes monouso."
                  constraints:
                    nullable: false

              - column:
                  name: ultimo_codice_usato
                  type: character varying(10)
                  remarks: "Anti-replay: ultimo codice TOTP verificato con successo."
                  constraints:
                    nullable: true

              - column:
                  name: ultimo_uso_at
                  type: timestamp with time zone
                  remarks: "Timestamp ultima verifica TOTP riuscita."
                  constraints:
                    nullable: true

              - column:
                  name: meta
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  constraints:
                    nullable: false

              - column:
                  name: data_insert
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_insert
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

              - column:
                  name: data_update
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_update
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

        - addUniqueConstraint:
            schemaName: config
            tableName: auth_totp_device
            columnNames: auth_user_id
            constraintName: uq_auth_totp_device_auth_user

      rollback:
        - dropTable:
            schemaName: config
            tableName: auth_totp_device
```

---

### A.1.6 ALTER `anagrafiche.risorse_umane_auth_user` — Fase 1+3

**File**: `00_schema/anagrafiche/20260328-06-alter-risorse-umane-auth-user-add-auth-flags-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Aggiunge colonne per gestione autenticazione avanzata:
#   deve_cambiare_password: cambio password obbligatorio (Fase 1)
#   invito_inviato_at: tracking invito operatore (Fase 3)
# ------------------------------------------------------------

databaseChangeLog:
    - logicalFilePath: migrations_v2/00_schema/anagrafiche/20260328-06-alter-risorse-umane-auth-user-add-auth-flags-mctit.yaml

    - changeSet:
          id: 20260328-06-alter-risorse-umane-auth-user-add-auth-flags
          author: mctit
          comment: >
            Aggiunge deve_cambiare_password (Fase 1 - cambio password obbligatorio)
            e invito_inviato_at (Fase 3 - tracking invito operatore).
          changes:
              - addColumn:
                    schemaName: anagrafiche
                    tableName: risorse_umane_auth_user
                    columns:
                        - column:
                              name: deve_cambiare_password
                              type: boolean
                              defaultValueBoolean: false
                              constraints:
                                  nullable: false
                              remarks: "Se true, l'operatore deve cambiare password al prossimo login. Impostato a true alla creazione o su richiesta admin."
                        - column:
                              name: invito_inviato_at
                              type: timestamp with time zone
                              constraints:
                                  nullable: true
                              remarks: "Timestamp ultimo invito inviato. NULL = mai invitato."

          rollback:
              - dropColumn:
                    schemaName: anagrafiche
                    tableName: risorse_umane_auth_user
                    columnName: deve_cambiare_password
              - dropColumn:
                    schemaName: anagrafiche
                    tableName: risorse_umane_auth_user
                    columnName: invito_inviato_at
```

---

### A.1.7 ALTER `anagrafiche.risorse_umane_auth_user` — Fase 4

**File**: `00_schema/anagrafiche/20260328-07-alter-risorse-umane-auth-user-add-totp-obbligatorio-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Aggiunge flag totp_obbligatorio per 2FA obbligatorio.
# Fase: 4 (2FA TOTP)
# ------------------------------------------------------------

databaseChangeLog:
    - logicalFilePath: migrations_v2/00_schema/anagrafiche/20260328-07-alter-risorse-umane-auth-user-add-totp-obbligatorio-mctit.yaml

    - changeSet:
          id: 20260328-07-alter-risorse-umane-auth-user-add-totp-obbligatorio
          author: mctit
          comment: >
            Aggiunge totp_obbligatorio: se true l'operatore DEVE
            configurare il 2FA per accedere al sistema.
          changes:
              - addColumn:
                    schemaName: anagrafiche
                    tableName: risorse_umane_auth_user
                    columns:
                        - column:
                              name: totp_obbligatorio
                              type: boolean
                              defaultValueBoolean: false
                              constraints:
                                  nullable: false
                              remarks: "Se true, l'operatore DEVE configurare il 2FA TOTP per accedere."

          rollback:
              - dropColumn:
                    schemaName: anagrafiche
                    tableName: risorse_umane_auth_user
                    columnName: totp_obbligatorio
```

---

### A.1.8 `config.email_outbox`

**File**: `00_schema/config/20260328-08-create-email-outbox-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Bozze email preparate dal sistema, editabili dall'operatore
# prima dell'invio. Flusso: template -> bozza -> anteprima -> invio.
# Fase: 1 (BB-1 Sistema Email Generico - Outbox)
# ------------------------------------------------------------

databaseChangeLog:
  - logicalFilePath: migrations_v2/00_schema/config/20260328-08-create-email-outbox-mctit.yaml

  - changeSet:
      id: 20260328-08-create-email-outbox
      author: mctit
      comment: >
        Bozze email editabili. Il sistema prepara la bozza dal template,
        l'operatore puo' modificare oggetto/corpo/CC prima dell'invio.
        Stato: DRAFT -> READY -> SENT (o CANCELLED).
      changes:
        - createTable:
            schemaName: config
            tableName: email_outbox
            remarks: "Bozze email editabili prima dell'invio."
            columns:
              - column:
                  name: id
                  type: bigint
                  autoIncrement: true
                  generationType: BY DEFAULT
                  remarks: "PK tecnica."
                  constraints:
                    primaryKey: true
                    primaryKeyName: pk_email_outbox
                    nullable: false

              - column:
                  name: email_account_id
                  type: integer
                  remarks: "FK account SMTP che sara' usato per l'invio."
                  constraints:
                    nullable: true

              - column:
                  name: email_template_id
                  type: integer
                  remarks: "FK template di origine (per riferimento). NULL se composta manualmente."
                  constraints:
                    nullable: true

              - column:
                  name: ambito
                  type: character varying(20)
                  defaultValue: "SISTEMA"
                  remarks: "Ambito visibilita': SISTEMA (solo admin), REPARTO (operatori UO), OPERATORE (solo creatore)."
                  constraints:
                    nullable: false

              - column:
                  name: unita_organizzativa_id
                  type: integer
                  remarks: "FK reparto proprietario. Obbligatorio se ambito=REPARTO."
                  constraints:
                    nullable: true

              - column:
                  name: pratica_id
                  type: bigint
                  remarks: "FK pratica collegata. Se presente, la email e' visibile dalla scheda pratica."
                  constraints:
                    nullable: true

              - column:
                  name: destinatario
                  type: character varying(255)
                  remarks: "Indirizzo email destinatario principale."
                  constraints:
                    nullable: false

              - column:
                  name: destinatari_cc
                  type: text[]
                  remarks: "Array indirizzi CC (opzionale)."
                  constraints:
                    nullable: true

              - column:
                  name: oggetto
                  type: text
                  remarks: "Oggetto email pre-compilato dal template, editabile."
                  constraints:
                    nullable: false

              - column:
                  name: corpo_html
                  type: text
                  remarks: "Corpo HTML pre-compilato e renderizzato, editabile."
                  constraints:
                    nullable: false

              - column:
                  name: corpo_testo
                  type: text
                  remarks: "Corpo plaintext (opzionale, editabile)."
                  constraints:
                    nullable: true

              - column:
                  name: stato
                  type: character varying(20)
                  defaultValue: "DRAFT"
                  remarks: "Stato bozza: DRAFT, READY, SENT, CANCELLED."
                  constraints:
                    nullable: false

              - column:
                  name: contesto_json
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  remarks: "Variabili usate per il rendering iniziale dal template."
                  constraints:
                    nullable: false

              - column:
                  name: auth_user_id
                  type: integer
                  remarks: "FK operatore destinatario (se applicabile)."
                  constraints:
                    nullable: true

              - column:
                  name: creato_da_user_id
                  type: integer
                  remarks: "FK operatore che ha creato la bozza."
                  constraints:
                    nullable: true

              - column:
                  name: inviato_at
                  type: timestamp with time zone
                  remarks: "Timestamp invio effettivo."
                  constraints:
                    nullable: true

              - column:
                  name: email_log_id
                  type: bigint
                  remarks: "FK al record email_log creato dopo l'invio."
                  constraints:
                    nullable: true

              - column:
                  name: tx_id
                  type: uuid
                  remarks: "Transaction ID per correlazione audit."
                  constraints:
                    nullable: true

              - column:
                  name: meta
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  constraints:
                    nullable: false

              - column:
                  name: data_insert
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_insert
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

              - column:
                  name: data_update
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_update
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_outbox
            baseColumnNames: email_account_id
            referencedTableSchemaName: config
            referencedTableName: email_account
            referencedColumnNames: id
            constraintName: fk_email_outbox_email_account
            onUpdate: NO ACTION
            onDelete: SET NULL

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_outbox
            baseColumnNames: email_template_id
            referencedTableSchemaName: config
            referencedTableName: email_template
            referencedColumnNames: id
            constraintName: fk_email_outbox_email_template
            onUpdate: NO ACTION
            onDelete: SET NULL

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_outbox
            baseColumnNames: email_log_id
            referencedTableSchemaName: config
            referencedTableName: email_log
            referencedColumnNames: id
            constraintName: fk_email_outbox_email_log
            onUpdate: NO ACTION
            onDelete: SET NULL

        - createIndex:
            schemaName: config
            tableName: email_outbox
            indexName: ix_email_outbox_stato_creato_da
            columns:
              - column:
                  name: stato
              - column:
                  name: creato_da_user_id

        - sql:
            sql: |
              ALTER TABLE config.email_outbox
                ADD CONSTRAINT chk_email_outbox_stato
                CHECK (stato IN ('DRAFT', 'READY', 'SENT', 'CANCELLED'));

              COMMENT ON TABLE config.email_outbox
                IS 'Bozze email editabili. Flusso: template renderizzato -> bozza DRAFT -> anteprima/modifica -> SENT o CANCELLED.';

      rollback:
        - dropTable:
            schemaName: config
            tableName: email_outbox
```

---

### A.1.9 `config.email_allegato`

**File**: `00_schema/config/20260328-09-create-email-allegato-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Allegati email associati a bozze outbox o log email.
# File salvati su filesystem, non in DB.
# Fase: 1 (BB-1 Sistema Email Generico - Allegati)
# ------------------------------------------------------------

databaseChangeLog:
  - logicalFilePath: migrations_v2/00_schema/config/20260328-09-create-email-allegato-mctit.yaml

  - changeSet:
      id: 20260328-09-create-email-allegato
      author: mctit
      comment: >
        Allegati email. Associati a email_outbox (bozza) o email_log (storico).
        Il file fisico e' su filesystem (path relativo in file_path).
        Origine: UPLOAD (caricato dall'operatore) o TEMPLATE (default del template).
      changes:
        - createTable:
            schemaName: config
            tableName: email_allegato
            remarks: "Allegati email su filesystem, associati a outbox o log."
            columns:
              - column:
                  name: id
                  type: bigint
                  autoIncrement: true
                  generationType: BY DEFAULT
                  remarks: "PK tecnica."
                  constraints:
                    primaryKey: true
                    primaryKeyName: pk_email_allegato
                    nullable: false

              - column:
                  name: email_outbox_id
                  type: bigint
                  remarks: "FK bozza email (NULL dopo invio se copiato su log)."
                  constraints:
                    nullable: true

              - column:
                  name: email_log_id
                  type: bigint
                  remarks: "FK log email (popolato dopo invio per consultazione storica)."
                  constraints:
                    nullable: true

              - column:
                  name: nome_file
                  type: character varying(255)
                  remarks: "Nome originale del file (es. guida-utente.pdf)."
                  constraints:
                    nullable: false

              - column:
                  name: mime_type
                  type: character varying(100)
                  remarks: "Tipo MIME (es. application/pdf, image/png)."
                  constraints:
                    nullable: false

              - column:
                  name: dimensione_bytes
                  type: bigint
                  remarks: "Dimensione file in bytes."
                  constraints:
                    nullable: false

              - column:
                  name: file_path
                  type: character varying(512)
                  remarks: "Percorso relativo nello storage (es. email_attachments/2026/03/uuid.pdf)."
                  constraints:
                    nullable: false

              - column:
                  name: origine
                  type: character varying(20)
                  defaultValue: "UPLOAD"
                  remarks: "Origine: UPLOAD (caricato dall'operatore) o TEMPLATE (default del template)."
                  constraints:
                    nullable: false

              - column:
                  name: meta
                  type: jsonb
                  defaultValueComputed: "'{}'::jsonb"
                  constraints:
                    nullable: false

              - column:
                  name: data_insert
                  type: timestamp with time zone
                  defaultValueComputed: "now()"
                  constraints:
                    nullable: false

              - column:
                  name: user_insert
                  type: text
                  defaultValueComputed: "CURRENT_USER"
                  constraints:
                    nullable: false

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_allegato
            baseColumnNames: email_outbox_id
            referencedTableSchemaName: config
            referencedTableName: email_outbox
            referencedColumnNames: id
            constraintName: fk_email_allegato_outbox
            onUpdate: NO ACTION
            onDelete: CASCADE

        - addForeignKeyConstraint:
            baseTableSchemaName: config
            baseTableName: email_allegato
            baseColumnNames: email_log_id
            referencedTableSchemaName: config
            referencedTableName: email_log
            referencedColumnNames: id
            constraintName: fk_email_allegato_log
            onUpdate: NO ACTION
            onDelete: SET NULL

        - createIndex:
            schemaName: config
            tableName: email_allegato
            indexName: ix_email_allegato_outbox_id
            columns:
              - column:
                  name: email_outbox_id

        - createIndex:
            schemaName: config
            tableName: email_allegato
            indexName: ix_email_allegato_log_id
            columns:
              - column:
                  name: email_log_id

        - sql:
            sql: |
              ALTER TABLE config.email_allegato
                ADD CONSTRAINT chk_email_allegato_origine
                CHECK (origine IN ('UPLOAD', 'TEMPLATE'));

              ALTER TABLE config.email_allegato
                ADD CONSTRAINT chk_email_allegato_dimensione
                CHECK (dimensione_bytes > 0);

              COMMENT ON TABLE config.email_allegato
                IS 'Allegati email su filesystem. Associati a outbox (bozza) o log (storico invio). ON DELETE CASCADE su outbox.';

      rollback:
        - dropTable:
            schemaName: config
            tableName: email_allegato
```

---

### A.1.10 ALTER `config.email_log` — corpo inviato, ambito, pratica, outbox

**File**: `00_schema/config/20260328-10-alter-email-log-add-corpo-inviato-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Aggiunge: corpo inviato (consultazione fedele post-invio),
# ambito visibilita' (SISTEMA/REPARTO/OPERATORE),
# collegamento a pratica e bozza outbox.
# Fase: 1 (BB-1 Sistema Email Generico)
# ------------------------------------------------------------

databaseChangeLog:
    - logicalFilePath: migrations_v2/00_schema/config/20260328-10-alter-email-log-add-corpo-inviato-mctit.yaml

    - changeSet:
          id: 20260328-10-alter-email-log-add-corpo-inviato
          author: mctit
          comment: >
            Aggiunge corpo_inviato_html/testo, destinatari_cc,
            ambito (SISTEMA/REPARTO/OPERATORE), unita_organizzativa_id,
            pratica_id, email_outbox_id.
          changes:
              - addColumn:
                    schemaName: config
                    tableName: email_log
                    columns:
                        - column:
                              name: corpo_inviato_html
                              type: text
                              constraints:
                                  nullable: true
                              remarks: "Corpo HTML esattamente come inviato (dopo eventuali modifiche manuali)."
                        - column:
                              name: corpo_inviato_testo
                              type: text
                              constraints:
                                  nullable: true
                              remarks: "Corpo plaintext esattamente come inviato."
                        - column:
                              name: destinatari_cc
                              type: text[]
                              constraints:
                                  nullable: true
                              remarks: "Indirizzi CC usati nell'invio."
                        - column:
                              name: ambito
                              type: character varying(20)
                              defaultValue: "SISTEMA"
                              constraints:
                                  nullable: false
                              remarks: "Ambito visibilita': SISTEMA (solo admin), REPARTO (operatori UO), OPERATORE (solo creatore)."
                        - column:
                              name: unita_organizzativa_id
                              type: integer
                              constraints:
                                  nullable: true
                              remarks: "Reparto proprietario. Obbligatorio se ambito=REPARTO."
                        - column:
                              name: pratica_id
                              type: bigint
                              constraints:
                                  nullable: true
                              remarks: "Pratica collegata. Consultabile dalla scheda pratica."
                        - column:
                              name: email_outbox_id
                              type: bigint
                              constraints:
                                  nullable: true
                              remarks: "FK bozza di origine (NULL se invio diretto senza anteprima)."

              - addForeignKeyConstraint:
                    baseTableSchemaName: config
                    baseTableName: email_log
                    baseColumnNames: email_outbox_id
                    referencedTableSchemaName: config
                    referencedTableName: email_outbox
                    referencedColumnNames: id
                    constraintName: fk_email_log_outbox
                    onUpdate: NO ACTION
                    onDelete: SET NULL

              - addForeignKeyConstraint:
                    baseTableSchemaName: config
                    baseTableName: email_log
                    baseColumnNames: unita_organizzativa_id
                    referencedTableSchemaName: config
                    referencedTableName: unita_organizzative
                    referencedColumnNames: id
                    constraintName: fk_email_log_unita_organizzativa
                    onUpdate: NO ACTION
                    onDelete: SET NULL

              - addForeignKeyConstraint:
                    baseTableSchemaName: config
                    baseTableName: email_log
                    baseColumnNames: pratica_id
                    referencedTableSchemaName: pratiche
                    referencedTableName: pratiche
                    referencedColumnNames: id
                    constraintName: fk_email_log_pratica
                    onUpdate: NO ACTION
                    onDelete: SET NULL

              - createIndex:
                    schemaName: config
                    tableName: email_log
                    indexName: ix_email_log_pratica_id
                    columns:
                      - column:
                          name: pratica_id

              - createIndex:
                    schemaName: config
                    tableName: email_log
                    indexName: ix_email_log_ambito_uo
                    columns:
                      - column:
                          name: ambito
                      - column:
                          name: unita_organizzativa_id

              - sql:
                    sql: |
                      ALTER TABLE config.email_log
                        ADD CONSTRAINT chk_email_log_ambito
                        CHECK (ambito IN ('SISTEMA', 'REPARTO', 'OPERATORE'));

          rollback:
              - dropColumn:
                    schemaName: config
                    tableName: email_log
                    columnName: corpo_inviato_html
              - dropColumn:
                    schemaName: config
                    tableName: email_log
                    columnName: corpo_inviato_testo
              - dropColumn:
                    schemaName: config
                    tableName: email_log
                    columnName: destinatari_cc
              - dropColumn:
                    schemaName: config
                    tableName: email_log
                    columnName: ambito
              - dropColumn:
                    schemaName: config
                    tableName: email_log
                    columnName: unita_organizzativa_id
              - dropColumn:
                    schemaName: config
                    tableName: email_log
                    columnName: pratica_id
              - dropColumn:
                    schemaName: config
                    tableName: email_log
                    columnName: email_outbox_id
```

---

## A.2 Funzioni (20_code)

### A.2.1 `config.fn_resolve_email_account`

**File**: `20_code/config/20260328-01-create-fn-resolve-email-account-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Risolve l'account email da usare per un dato reparto.
# Catena di fallback: reparto -> account di sistema (codice 'SISTEMA').
# Fase: 1 (BB-1 Sistema Email Generico)
# ------------------------------------------------------------

databaseChangeLog:
    - logicalFilePath: migrations_v2/20_code/config/20260328-01-create-fn-resolve-email-account-mctit.yaml

    - changeSet:
          id: 20260328-01-create-fn-resolve-email-account
          author: mctit
          comment: >
            Risolve l'account email SMTP per un dato reparto.
            Fallback: account specifico del reparto -> account SISTEMA.
            Ritorna JSONB con i dati dell'account (esclusa password).
          runOnChange: true
          changes:
              - sql:
                    splitStatements: false
                    stripComments: false
                    sql: |

                        CREATE OR REPLACE FUNCTION config.fn_resolve_email_account(
                            p_unita_organizzativa_id  config.email_account.unita_organizzativa_id%TYPE
                                                      DEFAULT NULL
                        )
                        RETURNS jsonb
                        LANGUAGE plpgsql
                        STABLE
                        AS $function$
                        DECLARE
                            v_result jsonb;
                        BEGIN
                            -- =========================================================
                            -- Scopo:
                            --   Risolve l'account SMTP da usare per l'invio email.
                            --   Catena di fallback:
                            --     1. Account specifico del reparto (unita_organizzativa_id)
                            --     2. Account di sistema (codice = 'SISTEMA')
                            --
                            -- Parametri:
                            --   p_unita_organizzativa_id: ID reparto (NULL = usa diretto SISTEMA)
                            --
                            -- Restituisce:
                            --   JSONB con: id, codice, smtp_host, smtp_port, smtp_use_tls,
                            --   smtp_use_ssl, smtp_username, smtp_password_encrypted,
                            --   email_from, email_reply_to.
                            --   NULL se nessun account attivo trovato.
                            -- =========================================================

                            -- 1. Tentativo: account specifico del reparto
                            IF p_unita_organizzativa_id IS NOT NULL THEN
                                SELECT jsonb_build_object(
                                    'id',                      ea.id,
                                    'codice',                  ea.codice,
                                    'smtp_host',               ea.smtp_host,
                                    'smtp_port',               ea.smtp_port,
                                    'smtp_use_tls',            ea.smtp_use_tls,
                                    'smtp_use_ssl',            ea.smtp_use_ssl,
                                    'smtp_username',           ea.smtp_username,
                                    'smtp_password_encrypted', ea.smtp_password_encrypted,
                                    'email_from',              ea.email_from,
                                    'email_reply_to',          ea.email_reply_to
                                )
                                INTO v_result
                                FROM config.email_account ea
                                WHERE ea.unita_organizzativa_id = p_unita_organizzativa_id
                                  AND ea.attivo = true
                                ORDER BY ea.id
                                LIMIT 1;

                                IF v_result IS NOT NULL THEN
                                    RETURN v_result;
                                END IF;
                            END IF;

                            -- 2. Fallback: account di sistema
                            SELECT jsonb_build_object(
                                'id',                      ea.id,
                                'codice',                  ea.codice,
                                'smtp_host',               ea.smtp_host,
                                'smtp_port',               ea.smtp_port,
                                'smtp_use_tls',            ea.smtp_use_tls,
                                'smtp_use_ssl',            ea.smtp_use_ssl,
                                'smtp_username',           ea.smtp_username,
                                'smtp_password_encrypted', ea.smtp_password_encrypted,
                                'email_from',              ea.email_from,
                                'email_reply_to',          ea.email_reply_to
                            )
                            INTO v_result
                            FROM config.email_account ea
                            WHERE ea.codice = 'SISTEMA'
                              AND ea.attivo = true;

                            RETURN v_result;
                        END;
                        $function$;

                        COMMENT ON FUNCTION config.fn_resolve_email_account(integer)
                          IS 'Risolve account SMTP per invio email. Fallback: reparto -> SISTEMA. Ritorna JSONB con dati account (inclusa password crittografata).';
```

---

### A.2.2 `config.fn_resolve_email_template`

**File**: `20_code/config/20260328-02-create-fn-resolve-email-template-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Risolve il template email per codice, reparto, tipo pratica e lingua.
# Catena di fallback a 5 livelli:
#   1. reparto + tipo pratica + lingua
#   2. reparto + lingua (senza tipo pratica)
#   3. sistema + tipo pratica + lingua
#   4. sistema + lingua
#   5. sistema + lingua 'it'
# Fase: 1 (BB-1 Sistema Email Generico)
# ------------------------------------------------------------

databaseChangeLog:
    - logicalFilePath: migrations_v2/20_code/config/20260328-02-create-fn-resolve-email-template-mctit.yaml

    - changeSet:
          id: 20260328-02-create-fn-resolve-email-template
          author: mctit
          comment: >
            Risolve template email per codice, reparto, tipo pratica e lingua.
            Catena di fallback a 5 livelli per specializzazione progressiva.
          runOnChange: true
          changes:
              - sql:
                    splitStatements: false
                    stripComments: false
                    sql: |

                        CREATE OR REPLACE FUNCTION config.fn_resolve_email_template(
                            p_codice                  config.email_template.codice%TYPE,
                            p_unita_organizzativa_id  config.email_template.unita_organizzativa_id%TYPE
                                                      DEFAULT NULL,
                            p_tipo_prestazione_id         config.email_template.tipo_prestazione_id%TYPE
                                                      DEFAULT NULL,
                            p_lingua                  config.email_template.lingua%TYPE
                                                      DEFAULT 'it'
                        )
                        RETURNS jsonb
                        LANGUAGE plpgsql
                        STABLE
                        AS $function$
                        DECLARE
                            v_result jsonb;
                        BEGIN
                            -- =========================================================
                            -- Scopo:
                            --   Risolve il template email dato codice, reparto,
                            --   tipo pratica e lingua.
                            --   Catena di fallback (primo trovato attivo):
                            --     1. Reparto + tipo pratica + lingua
                            --     2. Reparto + lingua (senza tipo pratica)
                            --     3. Sistema + tipo pratica + lingua
                            --     4. Sistema + lingua
                            --     5. Sistema + lingua 'it' (fallback finale)
                            --
                            -- Parametri:
                            --   p_codice: codice tipo template (es. COMUNICAZIONE_PRATICA)
                            --   p_unita_organizzativa_id: ID reparto (NULL = solo sistema)
                            --   p_tipo_prestazione_id: ID tipo prestazione (NULL = generico)
                            --   p_lingua: codice lingua ISO (default 'it')
                            --
                            -- Restituisce:
                            --   JSONB con: id, codice, oggetto, corpo_html, corpo_testo,
                            --   variabili_disponibili, lingua.
                            --   NULL se nessun template attivo trovato.
                            -- =========================================================

                            IF p_codice IS NULL THEN
                                RETURN NULL;
                            END IF;

                            -- Helper: SELECT base per evitare ripetizione
                            -- (ogni step e' esplicito per chiarezza e performance)

                            -- 1. Reparto + tipo pratica + lingua
                            IF p_unita_organizzativa_id IS NOT NULL AND p_tipo_prestazione_id IS NOT NULL THEN
                                SELECT jsonb_build_object(
                                    'id',                     et.id,
                                    'codice',                 et.codice,
                                    'oggetto',                et.oggetto,
                                    'corpo_html',             et.corpo_html,
                                    'corpo_testo',            et.corpo_testo,
                                    'variabili_disponibili',  et.variabili_disponibili,
                                    'lingua',                 et.lingua
                                )
                                INTO v_result
                                FROM config.email_template et
                                WHERE et.codice = p_codice
                                  AND et.unita_organizzativa_id = p_unita_organizzativa_id
                                  AND et.tipo_prestazione_id = p_tipo_prestazione_id
                                  AND et.lingua = p_lingua
                                  AND et.attivo = true;

                                IF v_result IS NOT NULL THEN
                                    RETURN v_result;
                                END IF;
                            END IF;

                            -- 2. Reparto + lingua (senza tipo pratica)
                            IF p_unita_organizzativa_id IS NOT NULL THEN
                                SELECT jsonb_build_object(
                                    'id',                     et.id,
                                    'codice',                 et.codice,
                                    'oggetto',                et.oggetto,
                                    'corpo_html',             et.corpo_html,
                                    'corpo_testo',            et.corpo_testo,
                                    'variabili_disponibili',  et.variabili_disponibili,
                                    'lingua',                 et.lingua
                                )
                                INTO v_result
                                FROM config.email_template et
                                WHERE et.codice = p_codice
                                  AND et.unita_organizzativa_id = p_unita_organizzativa_id
                                  AND et.tipo_prestazione_id IS NULL
                                  AND et.lingua = p_lingua
                                  AND et.attivo = true;

                                IF v_result IS NOT NULL THEN
                                    RETURN v_result;
                                END IF;
                            END IF;

                            -- 3. Sistema + tipo pratica + lingua
                            IF p_tipo_prestazione_id IS NOT NULL THEN
                                SELECT jsonb_build_object(
                                    'id',                     et.id,
                                    'codice',                 et.codice,
                                    'oggetto',                et.oggetto,
                                    'corpo_html',             et.corpo_html,
                                    'corpo_testo',            et.corpo_testo,
                                    'variabili_disponibili',  et.variabili_disponibili,
                                    'lingua',                 et.lingua
                                )
                                INTO v_result
                                FROM config.email_template et
                                WHERE et.codice = p_codice
                                  AND et.unita_organizzativa_id IS NULL
                                  AND et.tipo_prestazione_id = p_tipo_prestazione_id
                                  AND et.lingua = p_lingua
                                  AND et.attivo = true;

                                IF v_result IS NOT NULL THEN
                                    RETURN v_result;
                                END IF;
                            END IF;

                            -- 4. Sistema + lingua richiesta (senza tipo pratica)
                            SELECT jsonb_build_object(
                                'id',                     et.id,
                                'codice',                 et.codice,
                                'oggetto',                et.oggetto,
                                'corpo_html',             et.corpo_html,
                                'corpo_testo',            et.corpo_testo,
                                'variabili_disponibili',  et.variabili_disponibili,
                                'lingua',                 et.lingua
                            )
                            INTO v_result
                            FROM config.email_template et
                            WHERE et.codice = p_codice
                              AND et.unita_organizzativa_id IS NULL
                              AND et.tipo_prestazione_id IS NULL
                              AND et.lingua = p_lingua
                              AND et.attivo = true;

                            IF v_result IS NOT NULL THEN
                                RETURN v_result;
                            END IF;

                            -- 5. Fallback finale: sistema + lingua 'it'
                            IF p_lingua <> 'it' THEN
                                SELECT jsonb_build_object(
                                    'id',                     et.id,
                                    'codice',                 et.codice,
                                    'oggetto',                et.oggetto,
                                    'corpo_html',             et.corpo_html,
                                    'corpo_testo',            et.corpo_testo,
                                    'variabili_disponibili',  et.variabili_disponibili,
                                    'lingua',                 et.lingua
                                )
                                INTO v_result
                                FROM config.email_template et
                                WHERE et.codice = p_codice
                                  AND et.unita_organizzativa_id IS NULL
                                  AND et.tipo_prestazione_id IS NULL
                                  AND et.lingua = 'it'
                                  AND et.attivo = true;
                            END IF;

                            RETURN v_result;
                        END;
                        $function$;

                        COMMENT ON FUNCTION config.fn_resolve_email_template(character varying, integer, integer, character varying)
                          IS 'Risolve template email. Fallback a 5 livelli: reparto+tipo_pratica+lingua -> reparto+lingua -> sistema+tipo_pratica+lingua -> sistema+lingua -> sistema+it.';
```

---

### A.2.3 `config.fn_cleanup_token_scaduti`

**File**: `20_code/config/20260328-03-create-fn-cleanup-token-scaduti-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Pulizia periodica token scaduti o utilizzati.
# Eseguibile come job pgAgent.
# Fase: 1 (BB-2 Token Monouso Generico)
# ------------------------------------------------------------

databaseChangeLog:
    - logicalFilePath: migrations_v2/20_code/config/20260328-03-create-fn-cleanup-token-scaduti-mctit.yaml

    - changeSet:
          id: 20260328-03-create-fn-cleanup-token-scaduti
          author: mctit
          comment: >
            Elimina token scaduti o utilizzati da piu' di N giorni.
            Ritorna il numero di record eliminati.
            Eseguibile come job pgAgent periodico (es. ogni notte).
          runOnChange: true
          changes:
              - sql:
                    splitStatements: false
                    stripComments: false
                    sql: |

                        CREATE OR REPLACE FUNCTION config.fn_cleanup_token_scaduti(
                            p_giorni_retention  integer DEFAULT 30
                        )
                        RETURNS integer
                        LANGUAGE plpgsql
                        VOLATILE
                        AS $function$
                        DECLARE
                            v_deleted integer;
                        BEGIN
                            -- =========================================================
                            -- Scopo:
                            --   Elimina i token monouso che sono:
                            --   - scaduti da piu' di p_giorni_retention giorni, oppure
                            --   - utilizzati da piu' di p_giorni_retention giorni.
                            --   Pensato per esecuzione periodica (job pgAgent notturno).
                            --
                            -- Parametri:
                            --   p_giorni_retention: giorni di retention dopo scadenza/utilizzo
                            --                      (default 30)
                            --
                            -- Restituisce:
                            --   Numero di record eliminati.
                            -- =========================================================

                            IF p_giorni_retention IS NULL OR p_giorni_retention < 0 THEN
                                p_giorni_retention := 30;
                            END IF;

                            DELETE FROM config.token_monouso
                            WHERE
                                -- Token scaduti da piu' di N giorni
                                (scadenza < now() - make_interval(days => p_giorni_retention))
                                OR
                                -- Token utilizzati da piu' di N giorni
                                (utilizzato = true
                                 AND utilizzato_at < now() - make_interval(days => p_giorni_retention));

                            GET DIAGNOSTICS v_deleted = ROW_COUNT;
                            RETURN v_deleted;
                        END;
                        $function$;

                        COMMENT ON FUNCTION config.fn_cleanup_token_scaduti(integer)
                          IS 'Pulizia periodica token monouso scaduti/utilizzati. Default retention 30 giorni. Ritorna numero record eliminati.';
```

---

### A.2.4 `script.fn_check_operatore_invitabile`

**File**: `20_code/script/20260328-04-create-fn-check-operatore-invitabile-mctit.yaml`

```yaml
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025-2026 Tid (Michele Carlo Titini)
#
# Verifica se un operatore puo' ricevere un invito di primo accesso.
# Fase: 3 (Invito Operatore)
# ------------------------------------------------------------

databaseChangeLog:
    - logicalFilePath: migrations_v2/20_code/script/20260328-04-create-fn-check-operatore-invitabile-mctit.yaml

    - changeSet:
          id: 20260328-04-create-fn-check-operatore-invitabile
          author: mctit
          comment: >
            Verifica se un operatore e' invitabile: utente attivo,
            con email, mai loggato. Ritorna JSONB con esito e motivo.
          runOnChange: true
          changes:
              - sql:
                    splitStatements: false
                    stripComments: false
                    sql: |

                        CREATE OR REPLACE FUNCTION script.fn_check_operatore_invitabile(
                            p_auth_user_id  integer
                        )
                        RETURNS jsonb
                        LANGUAGE plpgsql
                        STABLE
                        AS $function$
                        DECLARE
                            v_is_active     boolean;
                            v_email         text;
                            v_last_login    timestamptz;
                            v_ruolo_sistema text;
                            v_rau_attivo    boolean;
                        BEGIN
                            -- =========================================================
                            -- Scopo:
                            --   Verifica se un operatore puo' ricevere un invito email
                            --   per il primo accesso al sistema.
                            --
                            -- Condizioni per essere invitabile:
                            --   1. auth_user esiste e is_active = true
                            --   2. risorse_umane_auth_user esiste e attivo = true
                            --   3. ruolo_sistema <> 'DISABILITATO'
                            --   4. auth_user ha un indirizzo email
                            --   5. auth_user.last_login IS NULL (mai loggato)
                            --
                            -- Parametri:
                            --   p_auth_user_id: ID utente Django
                            --
                            -- Restituisce:
                            --   JSONB: {invitabile: bool, motivo: text, email: text}
                            -- =========================================================

                            -- Guard: parametro obbligatorio
                            IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'auth_user_id non valido',
                                    'email', NULL
                                );
                            END IF;

                            -- Recupera dati auth_user
                            SELECT au.is_active, au.email, au.last_login
                              INTO v_is_active, v_email, v_last_login
                              FROM django.auth_user au
                             WHERE au.id = p_auth_user_id;

                            IF v_is_active IS NULL THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'Utente non trovato',
                                    'email', NULL
                                );
                            END IF;

                            IF v_is_active = false THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'Utente disattivato (is_active=false)',
                                    'email', v_email
                                );
                            END IF;

                            -- Recupera dati risorse_umane_auth_user
                            SELECT rau.ruolo_sistema::text, rau.attivo
                              INTO v_ruolo_sistema, v_rau_attivo
                              FROM anagrafiche.risorse_umane_auth_user rau
                             WHERE rau.auth_user_id = p_auth_user_id;

                            IF v_ruolo_sistema IS NULL THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'Nessun record risorse_umane_auth_user',
                                    'email', v_email
                                );
                            END IF;

                            IF v_rau_attivo = false THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'Record risorse_umane_auth_user non attivo',
                                    'email', v_email
                                );
                            END IF;

                            IF v_ruolo_sistema = 'DISABILITATO' THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'Ruolo sistema DISABILITATO',
                                    'email', v_email
                                );
                            END IF;

                            IF v_email IS NULL OR trim(v_email) = '' THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'Nessun indirizzo email configurato',
                                    'email', NULL
                                );
                            END IF;

                            IF v_last_login IS NOT NULL THEN
                                RETURN jsonb_build_object(
                                    'invitabile', false,
                                    'motivo', 'Utente ha gia'' effettuato login',
                                    'email', v_email
                                );
                            END IF;

                            -- Tutte le condizioni soddisfatte
                            RETURN jsonb_build_object(
                                'invitabile', true,
                                'motivo', NULL,
                                'email', v_email
                            );
                        END;
                        $function$;

                        COMMENT ON FUNCTION script.fn_check_operatore_invitabile(integer)
                          IS 'Verifica se operatore e'' invitabile: attivo, con email, mai loggato. Ritorna JSONB {invitabile, motivo, email}.';
```

---

### A.2.5 Aggiornamento `script.fn_get_user_profile` — flag auth

**File**: `20_code/script/20260328-05-update-fn-get-user-profile-auth-flags-mctit.yaml`

> **Nota**: questa migration aggiunge 3 chiavi al JSONB di ritorno:
> `deve_cambiare_password`, `totp_abilitato`, `totp_obbligatorio`.
> E' un `CREATE OR REPLACE` completo della funzione (runOnChange).

La modifica rispetto alla versione attuale (`20260320-02`) consiste in:

**1. Nuove variabili DECLARE** (dopo `v_rau_id`):

```sql
v_deve_cambiare_password  anagrafiche.risorse_umane_auth_user.deve_cambiare_password%TYPE;
v_totp_obbligatorio       anagrafiche.risorse_umane_auth_user.totp_obbligatorio%TYPE;
v_totp_abilitato          boolean;
```

**2. Modifica SELECT sezione 2** (risorse_umane_auth_user) — aggiungere colonne:

```sql
-- Riga esistente:
SELECT rau.id,
       rau.ruolo_sistema,
       rau.risorsa_umana_id
-- Diventa:
SELECT rau.id,
       rau.ruolo_sistema,
       rau.risorsa_umana_id,
       rau.deve_cambiare_password,
       rau.totp_obbligatorio
  INTO v_rau_id,
       v_ruolo_sistema,
       v_risorsa_umana_id,
       v_deve_cambiare_password,
       v_totp_obbligatorio
  FROM anagrafiche.risorse_umane_auth_user rau
 WHERE rau.auth_user_id = p_auth_user_id;
```

**3. Lookup TOTP** (dopo sezione 2, prima di sezione 3):

```sql
-- Verifica se 2FA configurato e abilitato
SELECT COALESCE(td.abilitato AND td.confermato, false)
  INTO v_totp_abilitato
  FROM config.auth_totp_device td
 WHERE td.auth_user_id = p_auth_user_id;

IF v_totp_abilitato IS NULL THEN
    v_totp_abilitato := false;
END IF;
```

**4. Aggiunta chiavi al risultato finale** (sezione 5):

```sql
-- Riga esistente:
v_result := jsonb_build_object(
    'utente',            v_utente,
    'ruolo_sistema',     v_ruolo_sistema,
    ...
    'azioni_abilitate',  script.fn_get_user_actions_map(p_auth_user_id)
);
-- Diventa:
v_result := jsonb_build_object(
    'utente',                   v_utente,
    'ruolo_sistema',            v_ruolo_sistema,
    'risorse_umane',            v_risorse_umane,
    'soggetto',                 v_soggetto,
    'emittente',                v_emittente,
    'permessi_area',            script.fn_get_user_permissions_map(p_auth_user_id),
    'azioni_abilitate',         script.fn_get_user_actions_map(p_auth_user_id),
    'deve_cambiare_password',   COALESCE(v_deve_cambiare_password, false),
    'totp_abilitato',           v_totp_abilitato,
    'totp_obbligatorio',        COALESCE(v_totp_obbligatorio, false)
);
```

> **Importante**: la migration completa deve essere un `CREATE OR REPLACE` con il body
> intero della funzione (copia dalla versione `20260320-02` e applica le 4 modifiche sopra).
> Non si puo' fare un ALTER parziale su una funzione PL/pgSQL.

---

## A.3 Seed Dati (80_data)

### A.3.1 Template email base

**File CSV**: `80_data/sql/config/email_template.csv`

```csv
id,codice,unita_organizzativa_id,lingua,oggetto,corpo_html,corpo_testo,variabili_disponibili,attivo,meta,data_insert,user_insert,data_update,user_update
1,INVITO_OPERATORE,,it,Benvenuto in {{azienda}} - Attiva il tuo account,"<h2>Benvenuto {{nome}} {{cognome}}!</h2><p>Sei stato invitato ad accedere al sistema <strong>{{azienda}}</strong>.</p><p>Clicca sul link seguente per attivare il tuo account e impostare la password:</p><p><a href=""{{link}}"">Attiva il tuo account</a></p><p>Il link scade tra {{scadenza_ore}} ore.</p><p>Se non hai richiesto questo invito, ignora questa email.</p><p>Cordiali saluti,<br/>{{invitato_da}}</p>","Benvenuto {{nome}} {{cognome}}! Sei stato invitato ad accedere al sistema {{azienda}}. Attiva il tuo account: {{link}} (scade tra {{scadenza_ore}} ore).","[""nome"",""cognome"",""azienda"",""link"",""scadenza_ore"",""invitato_da""]",true,{},now(),CURRENT_USER,now(),CURRENT_USER
2,RESET_PASSWORD,,it,Reset password - {{azienda}},"<h2>Reset password</h2><p>Ciao {{nome}},</p><p>Hai richiesto il reset della password per il tuo account su <strong>{{azienda}}</strong>.</p><p>Clicca sul link seguente per impostare una nuova password:</p><p><a href=""{{link}}"">Reimposta password</a></p><p>Il link scade tra {{scadenza_ore}} ore.</p><p>Se non hai richiesto questo reset, ignora questa email. La tua password attuale resta invariata.</p>","Ciao {{nome}}, hai richiesto il reset password per {{azienda}}. Link: {{link}} (scade tra {{scadenza_ore}} ore). Se non l'hai richiesto, ignora questa email.","[""nome"",""azienda"",""link"",""scadenza_ore""]",true,{},now(),CURRENT_USER,now(),CURRENT_USER
3,CAMBIO_PASSWORD_CONFERMA,,it,Password modificata - {{azienda}},"<h2>Password modificata</h2><p>Ciao {{nome}},</p><p>La password del tuo account su <strong>{{azienda}}</strong> e' stata modificata con successo il {{data_cambio}}.</p><p>Se non hai effettuato questa modifica, contatta immediatamente l'amministratore di sistema.</p>","Ciao {{nome}}, la password del tuo account su {{azienda}} e' stata modificata il {{data_cambio}}. Se non sei stato tu, contatta l'amministratore.","[""nome"",""azienda"",""data_cambio""]",true,{},now(),CURRENT_USER,now(),CURRENT_USER
4,NOTIFICA_GENERICA,,it,{{oggetto_custom}},"<p>{{corpo_custom}}</p>","{{corpo_custom}}","[""oggetto_custom"",""corpo_custom""]",true,{},now(),CURRENT_USER,now(),CURRENT_USER
```

**File YAML**: `80_data/changelog/20260328-70-upsert-config-email-template-mctit.yaml`

```yaml
databaseChangeLog:
  - logicalFilePath: migrations_v2/80_data/changelog/20260328-70-upsert-config-email-template-mctit.yaml

  - changeSet:
      id: 20260328-70-upsert-config-email-template
      author: mctit
      runOnChange: true
      validCheckSums:
        - ANY
      failOnError: true
      preConditions:
        - onFail: HALT
        - tableExists:
            schemaName: config
            tableName: email_template
      changes:
        - loadUpdateData:
            relativeToChangelogFile: true
            file: ../sql/config/email_template.csv
            tableName: email_template
            schemaName: config
            separator: ","
            encoding: UTF-8
            nullValue: ""
            primaryKey: "id"
            columns:
              - column: { name: id, type: STRING }
              - column: { name: codice, type: STRING }
              - column: { name: unita_organizzativa_id, type: NUMERIC }
              - column: { name: lingua, type: STRING }
              - column: { name: oggetto, type: STRING }
              - column: { name: corpo_html, type: STRING }
              - column: { name: corpo_testo, type: STRING }
              - column:
                  name: variabili_disponibili
                  type: JSON
                  defaultValue: "[]"
              - column: { name: attivo, type: BOOLEAN }
              - column:
                  name: meta
                  type: JSON
                  defaultValue: "{}"
              - column: { name: data_insert, type: STRING }
              - column: { name: user_insert, type: STRING }
              - column: { name: data_update, type: STRING }
              - column: { name: user_update, type: STRING }
```

---

## A.4 Riepilogo file — Tabelle (00_schema)

> I progressivi reali usati sono `-13` a `-19` (i precedenti `-01` a `-12` sono gia' occupati).
> I file sotto sono quelli **effettivamente creati** nel repo.

### Creati (Fase 1 — tabelle + ALTER)

| Progr. | Percorso | Oggetto | Stato |
| --- | --- | --- | --- |
| -13 | `00_schema/config/20260328-13-create-email-account-mctit.yaml` | Tabella `config.email_account` | ✅ |
| -14 | `00_schema/config/20260328-14-create-email-template-mctit.yaml` | Tabella `config.email_template` (con `tipo_prestazione_id`) | ✅ |
| -15 | `00_schema/config/20260328-15-create-email-log-mctit.yaml` | Tabella `config.email_log` (con ambito, pratica_id, corpo inviato) | ✅ |
| -16 | `00_schema/config/20260328-16-create-email-outbox-mctit.yaml` | Tabella `config.email_outbox` (con ambito, pratica_id) + FK circolari log | ✅ |
| -17 | `00_schema/config/20260328-17-create-email-allegato-mctit.yaml` | Tabella `config.email_allegato` | ✅ |
| -18 | `00_schema/config/20260328-18-create-token-monouso-mctit.yaml` | Tabella `config.token_monouso` | ✅ |
| -19 | `00_schema/anagrafiche/20260328-19-alter-risorse-umane-auth-user-add-auth-flags-mctit.yaml` | ALTER +2 colonne (`deve_cambiare_password`, `invito_inviato_at`) | ✅ |

### Da creare (Fase 4 — 2FA TOTP)

| Progr. | Percorso | Oggetto | Stato |
| --- | --- | --- | --- |
| -20 | `00_schema/config/20260328-20-create-auth-totp-device-mctit.yaml` | Tabella `config.auth_totp_device` | da fare |
| -21 | `00_schema/anagrafiche/20260328-21-alter-risorse-umane-auth-user-add-totp-obbligatorio-mctit.yaml` | ALTER +1 colonna (`totp_obbligatorio`) | da fare |

### Da creare (20_code — Funzioni)

| Progr. | Percorso | Oggetto | Stato |
| --- | --- | --- | --- |
| -22 | `20_code/config/20260328-22-create-fn-resolve-email-account-mctit.yaml` | Funzione risoluzione account | da fare |
| -23 | `20_code/config/20260328-23-create-fn-resolve-email-template-mctit.yaml` | Funzione risoluzione template (fallback 5 livelli) | da fare |
| -24 | `20_code/config/20260328-24-create-fn-cleanup-token-scaduti-mctit.yaml` | Funzione pulizia token | da fare |
| -25 | `20_code/script/20260328-25-create-fn-check-operatore-invitabile-mctit.yaml` | Funzione check invitabilita' | da fare |
| -26 | `20_code/script/20260328-26-update-fn-get-user-profile-auth-flags-mctit.yaml` | Update profilo utente +3 chiavi | da fare |

### Da creare (80_data — Seed)

| Progr. | Percorso | Oggetto | Stato |
| --- | --- | --- | --- |
| — | `80_data/sql/config/email_template.csv` | Seed template email base | da fare |
| -70 | `80_data/changelog/20260328-70-upsert-config-email-template-mctit.yaml` | Changelog seed template | da fare |

### Ordine di applicazione

```text
-- Fase 1 (tabelle):
-13 → -14 → -15 → -16 → -17 → -18 → -19

-- Fase 1 (funzioni + seed):
-22 → -23 → -24 → seed(-70) → -26(parziale: solo deve_cambiare_password)

-- Fase 3 (invito operatore):
-19 gia' applicato → -25

-- Fase 4 (2FA TOTP):
-20 → -21 → -26(completo, con lookup TOTP)
```

> **Nota su -26** (`fn_get_user_profile`): per Fase 1 basta aggiungere solo
> `deve_cambiare_password`. Le chiavi `totp_abilitato` e `totp_obbligatorio`
> si aggiungono in Fase 4 quando la tabella `auth_totp_device` esiste.
> Si possono fare 2 migration separate oppure una sola se si creano tutti
> gli oggetti DB insieme.
>
> **Nota sulle FK circolari** (-15/-16): `email_log.email_outbox_id` e
> `email_outbox.email_log_id` si referenziano a vicenda. La FK da log→outbox
> e' aggiunta nel changeset -16 (dopo che entrambe le tabelle esistono).
