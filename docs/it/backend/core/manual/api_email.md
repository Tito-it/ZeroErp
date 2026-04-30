# API Email — Sistema Email Generico

## Scopo

Sistema completo di invio email con risoluzione automatica account SMTP e template
per reparto/contesto. Supporta invio diretto, bozze editabili (outbox), allegati,
consultazione log. Ogni email e' tracciata in `config.email_log`.

## Contesto

Il sistema email e' un building block trasversale (Anello 0) usato da:

- Autenticazione: invito operatore, reset password, conferma cambio password
- Pratiche: comunicazioni ad-hoc dalla scheda pratica
- Notifiche: SLA in allarme, lotto completato, ecc.

Due modalita' di invio:

- **Console mode** (DEBUG + host SMTP vuoto): email loggata nel terminale Django + `email_log`
- **SMTP reale**: connessione SMTP per-account, con retry automatico

Ogni reparto (`config.unita_organizzative`) puo' avere il proprio account SMTP e template
personalizzati. Fallback automatico all'account/template di sistema (codice `SISTEMA`).

## Architettura a tre layer

```text
email_views.py (API)       — parsing, validazione input, ownership check, envelope
  |
email_service.py           — risoluzione account/template, rendering, invio SMTP/console
email_outbox_service.py    — gestione bozze, allegati, conferma invio
  |
email_repository.py        — SQL raw, chiamate fn_resolve_*, CRUD su 5 tabelle config
  |
PostgreSQL                 — email_account, email_template, email_log, email_outbox, email_allegato
                             fn_resolve_email_account, fn_resolve_email_template
```

## Dipendenze DB

| Tabella | Scopo |
| --- | --- |
| `config.email_account` | Account SMTP per reparto (con password Fernet) |
| `config.email_template` | Template parametrizzabili con override per reparto/tipo/lingua |
| `config.email_log` | Log immutabile di ogni invio (corpo esatto, stato, retry) |
| `config.email_outbox` | Bozze editabili prima dell'invio |
| `config.email_allegato` | File allegati a outbox/log |

| Funzione | Scopo |
| --- | --- |
| `config.fn_resolve_email_account(uo_id)` | Fallback: reparto → SISTEMA |
| `config.fn_resolve_email_template(codice, uo_id, tipo_prest_id, lingua)` | Fallback 5 livelli |
| `config.fn_cleanup_token_scaduti(giorni)` | Pulizia periodica token scaduti |

---

## Endpoint Admin — Account SMTP

Base path: `/api/v1/amm-software/`
Autenticazione: JWT + ruolo ADMIN (`AdminAPIView`)

### Lista account

```http
GET /api/v1/amm-software/email-accounts/
```

| Parametro | Tipo | Obbligatorio | Default | Note |
| --- | --- | :---: | --- | --- |
| `search` | string | No | — | ILIKE su codice, descrizione, email_from |
| `limit` | int | No | 50 | Max 200 |
| `offset` | int | No | 0 | — |

Risposta:

```json
{
  "data": {
    "count": 2,
    "results": [
      {
        "id": 1,
        "codice": "SISTEMA",
        "descrizione": "Account di sistema",
        "unita_organizzativa_id": null,
        "unita_organizzativa_descrizione": null,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_use_tls": true,
        "smtp_use_ssl": false,
        "smtp_username": "user@gmail.com",
        "email_from": "ZeroErp <user@gmail.com>",
        "email_reply_to": null,
        "attivo": true
      }
    ]
  }
}
```

> **Nota sicurezza**: la password SMTP non e' mai esposta nelle API. E' salvata
> crittografata con Fernet (chiave derivata da `SECRET_KEY`).

### Crea account

```http
POST /api/v1/amm-software/email-accounts/
```

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | :---: | --- |
| `codice` | string | Si | Convertito a UPPER, univoco |
| `descrizione` | string | Si | — |
| `smtp_host` | string | No | Vuoto = console mode in DEBUG |
| `smtp_port` | int | No | Default 587 |
| `smtp_use_tls` | bool | No | Default true |
| `smtp_use_ssl` | bool | No | Default false (mutuamente esclusivo con TLS) |
| `smtp_username` | string | No | — |
| `smtp_password` | string | No | Accettata in chiaro, salvata crittografata |
| `email_from` | string | Si | Es. `"Ufficio Acquisti <acq@azienda.it>"` |
| `email_reply_to` | string | No | — |
| `unita_organizzativa_id` | int | No | NULL = account di sistema |
| `attivo` | bool | No | Default true |

### Dettaglio / Modifica / Elimina

```http
GET    /api/v1/amm-software/email-accounts/{id}/
PATCH  /api/v1/amm-software/email-accounts/{id}/
DELETE /api/v1/amm-software/email-accounts/{id}/
```

PATCH accetta gli stessi campi del POST (tutti opzionali). Se `smtp_password`
e' fornita, viene ri-crittografata.

### Test connessione SMTP

```http
POST /api/v1/amm-software/email-accounts/{id}/test/
```

Body vuoto. Tenta login SMTP senza inviare email. In console mode (host vuoto
o `smtp.example.com`) ritorna successo diretto.

L'esito viene **persistito** in `config.email_account.meta` (chiavi
`last_test_outcome`, `last_test_at`, `last_test_message`) e ritornato nella
stessa risposta come parte del detail arricchito (Fase 6).

Risposta (success):

```json
{
  "data": {
    "success": true,
    "message": "Connessione SMTP riuscita.",
    "id": 12,
    "codice": "MAIN",
    "attivo": true,
    "smtp_host": "smtp.gmail.com",
    "can_test": true,
    "test_reason": null,
    "last_test_outcome": "SUCCESS",
    "last_test_at": "2026-04-29T22:00:00+00:00",
    "last_test_message": "Connessione SMTP riuscita."
  }
}
```

Risposta (failed):

```json
{
  "data": {
    "success": false,
    "message": "Errore SMTP: timeout",
    "id": 12,
    "can_test": true,
    "test_reason": null,
    "last_test_outcome": "FAILED",
    "last_test_at": "2026-04-29T22:01:00+00:00",
    "last_test_message": "Errore SMTP: timeout"
  }
}
```

### Capability test connessione (`can_test` / `test_reason`)

Il dettaglio account (`GET /email-accounts/{id}/`) include due campi che
guidano l'abilitazione del pulsante "Testa connessione" lato UI:

| Campo | Tipo | Significato |
| --- | --- | --- |
| `can_test` | bool | `true` se il pulsante test puo' essere abilitato |
| `test_reason` | string\|null | Chiave i18n del motivo quando `can_test=false` (tooltip) |
| `last_test_outcome` | string\|null | `SUCCESS`/`FAILED` dell'ultimo test, `null` se mai eseguito |
| `last_test_at` | string\|null | ISO-8601 UTC dell'ultimo test |
| `last_test_message` | string\|null | Messaggio diagnostico dell'ultimo test |

Logica di derivazione (`_derive_test_capability` in `email_views.py`):

1. Account non attivo → `can_test=False`, reason `amm.email_test_reason_inactive`.
2. Host vuoto o placeholder (`smtp.example.com`) → console mode, `can_test=True`
   anche senza password (nessuna connessione reale).
3. Host SMTP reale + password non configurata → `can_test=False`, reason
   `amm.email_test_reason_no_password`.
4. Host SMTP reale + password configurata → `can_test=True`.

---

## Endpoint Admin — Template Email

Base path: `/api/v1/amm-software/`

### Lista template

```http
GET /api/v1/amm-software/email-templates/
```

| Parametro | Tipo | Obbligatorio | Default | Note |
| --- | --- | :---: | --- | --- |
| `search` | string | No | — | ILIKE su codice, oggetto |
| `codice` | string | No | — | Filtro esatto per codice |
| `limit` | int | No | 50 | Max 200 |
| `offset` | int | No | 0 | — |

### Crea template

```http
POST /api/v1/amm-software/email-templates/
```

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | :---: | --- |
| `codice` | string | Si | UPPER, es. `INVITO_OPERATORE` |
| `oggetto` | string | Si | Supporta `{{variabili}}` |
| `corpo_html` | string | Si | Template HTML con `{{variabili}}` |
| `corpo_testo` | string | No | Versione plaintext |
| `lingua` | string | No | Default `it` |
| `unita_organizzativa_id` | int | No | NULL = template di sistema |
| `tipo_prestazione_id` | int | No | NULL = generico |
| `variabili_disponibili` | array | No | Es. `["nome", "link", "azienda"]` |
| `attivo` | bool | No | Default true |

### Dettaglio / Modifica / Elimina

```http
GET    /api/v1/amm-software/email-templates/{id}/
PATCH  /api/v1/amm-software/email-templates/{id}/
DELETE /api/v1/amm-software/email-templates/{id}/
```

### Preview template

```http
POST /api/v1/amm-software/email-templates/{id}/preview/
```

Body:

```json
{ "variabili": { "nome": "Mario", "azienda": "ZeroErp", "link": "https://..." } }
```

Risposta: oggetto e corpo renderizzati con le variabili fornite (senza invio).
Il `corpo_html` viene **sanificato** lato BE (Fase 6) tramite
`apps.core.services.html_sanitizer_service.sanitize_email_html`:

- Whitelist tag (`p`, `div`, `span`, `br`, `h1..h6`, `ul/ol/li`, `table/tr/td/th`,
  `a`, `img`, ecc.) — niente `<script>`, `<iframe>`, `<object>`, `<embed>`,
  `<form>`, `<style>`.
- Whitelist attributi per tag — niente attributi globali permissivi
  (rimossi `onclick`, `onerror`, ecc.).
- Whitelist protocolli URL: `http`, `https`, `mailto` — rimossi
  `javascript:`, `data:`, `file:`.
- Blocchi `<script>` e `<style>` rimossi insieme al loro contenuto
  (regex pre-bleach).
- Commenti HTML rimossi.

Il FE renderizza il `corpo_html` ricevuto dentro un `<iframe sandbox="" :srcdoc="">`
come **defense-in-depth**: anche se la sanificazione lato BE avesse una falla,
l'iframe sandbox (vuoto = nessun privilegio) impedisce esecuzione di script,
form, navigation, plugin, popup.

L'`oggetto` e' un header testuale (`Subject`) e non viene sanificato — solo
renderizzato con `render_template`.

---

## Endpoint Admin — Log Email

```http
GET /api/v1/amm-software/email-log/
GET /api/v1/amm-software/email-log/{id}/
```

Admin vede tutti gli ambiti. Filtri: `search`, `stato`, `ambito`, `pratica_id`,
`unita_organizzativa_id`, `limit`, `offset`.

Il dettaglio include `corpo_inviato_html` e `corpo_inviato_testo` (corpo esattamente
come inviato, anche se la bozza e' stata modificata prima dell'invio).

---

## Endpoint Operatore — Outbox (Bozze Email)

Base path: `/api/v1/core/`
Autenticazione: JWT (`DomainAPIView`, `skip_area_check=True`)

### Prepara bozza

```http
POST /api/v1/core/email/prepare/
```

Risolve template e account, renderizza variabili, crea bozza DRAFT editabile.

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | :---: | --- |
| `codice_template` | string | Si | Es. `INVITO_OPERATORE` |
| `destinatario` | string | Si | Email destinatario |
| `variabili` | object | No | Coppie chiave/valore per rendering |
| `destinatari_cc` | array | No | Indirizzi CC |
| `unita_organizzativa_id` | int | No | Per risoluzione account/template |
| `tipo_prestazione_id` | int | No | Per specializzazione template |
| `lingua` | string | No | Default `it` |
| `ambito` | string | No | `SISTEMA`/`REPARTO`/`OPERATORE` (default `SISTEMA`) |
| `pratica_id` | int | No | Collegamento a pratica |
| `auth_user_id` | int | No | Operatore destinatario |

Risposta: bozza completa con oggetto/corpo pre-compilati (editabili dal frontend).

### Lista bozze

```http
GET /api/v1/core/email/outbox/
```

L'operatore vede solo le proprie bozze. Superuser vede tutte.
Filtri: `stato`, `pratica_id`, `limit`, `offset`.

### Dettaglio / Modifica bozza

```http
GET   /api/v1/core/email/outbox/{id}/
PATCH /api/v1/core/email/outbox/{id}/
```

GET include lista allegati. PATCH accetta: `oggetto`, `corpo_html`, `corpo_testo`,
`destinatari_cc`, `destinatario`. Solo bozze DRAFT sono modificabili.

**Ownership check**: solo il creatore della bozza (o superuser) puo' accedere.

### Conferma e invia

```http
POST /api/v1/core/email/outbox/{id}/send/
```

Transizione: DRAFT → READY → SENT (se SMTP riuscito) oppure DRAFT → READY → DRAFT
(se SMTP fallito — l'operatore puo' riprovare). Crea record in `email_log` con corpo
dalla bozza (non dal template originale). Copia allegati su `email_log_id`.
Lo stato SMTP e' nel log (`SENT` o `FAILED`); lo stato outbox riflette se l'operatore
deve agire (DRAFT = da riprovare, SENT = completato).

### Annulla bozza

```http
POST /api/v1/core/email/outbox/{id}/cancel/
```

Transizione: DRAFT → CANCELLED. Elimina allegati fisici da storage.

---

## Endpoint Operatore — Allegati

### Upload allegato

```http
POST /api/v1/core/email/outbox/{id}/allegati/
Content-Type: multipart/form-data
```

Campo: `file` (multipart). Validazioni:

| Regola | Valore |
| --- | --- |
| MIME types ammessi | pdf, docx, xlsx, xls, doc, jpeg, png, gif, txt, csv |
| Dimensione massima | 10 MB (configurabile: `EMAIL_ATTACHMENT_MAX_SIZE_MB`) |
| Numero massimo per email | 10 (configurabile: `EMAIL_ATTACHMENT_MAX_COUNT`) |

Storage: `{EMAIL_ATTACHMENTS_ROOT}/{anno}/{mese}/{uuid}.{ext}`

### Lista allegati

```http
GET /api/v1/core/email/outbox/{id}/allegati/list/
```

### Elimina allegato

```http
DELETE /api/v1/core/email/allegati/{allegato_id}/
```

Elimina file fisico + record DB.

### Download allegato

```http
GET /api/v1/core/email/allegati/{allegato_id}/download/
```

Ritorna `FileResponse` con `Content-Disposition: attachment`. Guard anti-path-traversal
su `file_path`.

---

## Endpoint Operatore — Log Email

```http
GET /api/v1/core/email/log/
```

L'operatore vede le email del proprio ambito. Filtri: `search`, `stato`,
`pratica_id`, `limit`, `offset`.

---

## Risoluzione Account — Catena di Fallback

```text
Richiesta invio email (unita_organizzativa_id = 42)
  → fn_resolve_email_account(42)
  → 1. Account specifico del reparto 42 (attivo)
  → 2. Account di sistema (codice = 'SISTEMA', attivo)
  → NULL se nessuno trovato → errore E_EMAIL
```

## Risoluzione Template — Catena di Fallback (5 livelli)

```text
Richiesta template (codice='INVITO', uo_id=42, tipo_prest_id=7, lingua='en')
  → fn_resolve_email_template('INVITO', 42, 7, 'en')
  → 1. Reparto 42 + tipo 7 + lingua 'en'
  → 2. Reparto 42 + lingua 'en' (senza tipo)
  → 3. Sistema + tipo 7 + lingua 'en'
  → 4. Sistema + lingua 'en' (senza tipo)
  → 5. Sistema + lingua 'it' (fallback finale)
  → NULL se nessuno trovato → errore E_EMAIL
```

## Rendering Variabili

I template supportano variabili con sintassi `{{nome_variabile}}`.
Variabili non trovate nel dizionario restano invariate nel testo
(es. `{{link}}` rimane se `link` non e' tra le variabili).

## Ambito e Visibilita'

Ogni email (outbox e log) ha un campo `ambito`:

| Ambito | Significato | Visibilita' |
| --- | --- | --- |
| `SISTEMA` | Email infrastrutturali (inviti, reset) | Solo ADMIN |
| `REPARTO` | Email del reparto (comunicazioni a clienti/fornitori) | Operatori dell'unita' organizzativa + ADMIN |
| `OPERATORE` | Email personale dell'operatore | Solo il creatore + ADMIN |

Email con `pratica_id` sono visibili anche dalla scheda pratica.

## Management Command

```bash
# Processa email in coda (PENDING/RETRY)
python manage.py send_pending_emails

# Preview senza invio
python manage.py send_pending_emails --dry-run

# Limita a 10 email
python manage.py send_pending_emails --limit 10
```

Schedulabile come cron job (pgAgent o crontab). Per ogni email in coda, usa
l'`email_account_id` originale (non risolve da zero).

## Sicurezza

- Password SMTP crittografata con Fernet (chiave derivata da `SECRET_KEY`) — mai in chiaro in DB o API
- Guard su password NULL: `decrypt()` e `test_connection` gestiscono account senza password configurata
- Ownership check su tutte le operazioni outbox e allegati (fail-closed se nessun outbox padre)
- Path traversal guard su download allegati (`normpath` + `startswith`)
- Whitelist colonne aggiornabili nei metodi UPDATE del repository (previene SQL injection da kwargs)
- MIME type whitelist per upload allegati
- Template rendering sicuro: solo sostituzione `{{chiave}}`, nessuna esecuzione codice
- Outbox: stato riflette esito reale (SENT su successo, DRAFT su fallimento SMTP)
- SMTP catch specifico: `(SMTPException, OSError, ValueError)` — errori di programmazione non mascherati
- Connessione SMTP chiusa in `finally` (no connection leak)

## Settings Django

| Setting | Default | Scopo |
| --- | --- | --- |
| `EMAIL_BACKEND` | `console` | Backend Django (non usato direttamente, il service usa SMTP per-account) |
| `EMAIL_ATTACHMENTS_ROOT` | `{BASE_DIR}/email_attachments` | Root storage allegati |
| `EMAIL_ATTACHMENT_MAX_SIZE_MB` | 10 | Dimensione massima allegato in MB |
| `EMAIL_ATTACHMENT_MAX_COUNT` | 10 | Numero massimo allegati per email |

## File Python

| File | Scopo |
| --- | --- |
| `apps/core/services/crypto_service.py` | Fernet encrypt/decrypt |
| `apps/core/db/email_repository.py` | Repository: CRUD 5 tabelle + fn_resolve |
| `apps/core/services/email_service.py` | EmailDispatchService: resolve, render, send |
| `apps/core/services/email_outbox_service.py` | EmailOutboxService: bozze, allegati |
| `apps/amm_software/api/email_views.py` | API admin (account, template, log) |
| `apps/core/api/email_views.py` | API operatore (outbox, allegati, log) |
| `apps/core/management/commands/send_pending_emails.py` | Command coda email |
| `apps/core/api/constants.py` | DEFAULT_LIMIT, MAX_LIMIT condivisi |
