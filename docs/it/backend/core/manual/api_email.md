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

- **Console mode** (sempre con `DEBUG` attivo, **qualunque** sia l'host dell'account): email
  loggata nel terminale Django + `email_log` con stato `SIMULATA`
- **SMTP reale** (fuori da `DEBUG`, host configurato): connessione SMTP per-account, con retry
  automatico

Fuori da `DEBUG`, un account con host vuoto o `smtp.example.com` **non spedisce**: l'invio
viene registrato come non riuscito, col motivo (`canale_invio` in `email_service.py`).

Ogni reparto (`config.unita_organizzative`) puo' avere il proprio account SMTP e template
personalizzati. Fallback automatico all'account/template di sistema (codice `SISTEMA`).

## Architettura a tre layer

```text
email_views.py (API)       — parsing, validazione input, envelope (il perimetro lo tiene la RLS)
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
Autenticazione: JWT + ruolo `SUPER_ADMIN` (`AdminAPIView`)

### Lista account

```http
GET /api/v1/amm-software/email-accounts/
```

| Parametro | Tipo | Obbligatorio | Default | Note |
| --- | --- | :---: | --- | --- |
| `search` | string | No | — | Ricerca libera: le colonne le decide il catalogo della lista `config.email_account`. Da un carattere (tabella di configurazione) |
| `limit` | int | No | 25 | Max 200 |
| `offset` | int | No | 0 | — |
| `order_by` | string | No | `codice` | Colonna di ordinamento |
| `order_dir` | string | No | `asc` | `asc` / `desc` |

Risposta:

```json
{
  "data": {
    "count": 2,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
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
> crittografata con Fernet (chiavi `DJANGO_FIELD_ENCRYPTION_KEYS`, separate dalla `SECRET_KEY`).

### Crea account

```http
POST /api/v1/amm-software/email-accounts/
```

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | :---: | --- |
| `codice` | string | Si | Convertito a UPPER, univoco |
| `descrizione` | string | Si | — |
| `smtp_host` | string | No | Vuoto o `smtp.example.com` = l'account **non puo' spedire**: console mode in `DEBUG`, altrimenti invio rifiutato (vedi sotto) |
| `smtp_port` | int | No | Default 587 |
| `smtp_use_tls` | bool | No | Default true. Booleano JSON: `"false"`, `0` → 400 `E_VALIDATION_INPUT` col campo |
| `smtp_use_ssl` | bool | No | Default false (mutuamente esclusivo con TLS). Booleano JSON, come sopra |
| `smtp_username` | string | No | — |
| `smtp_password` | string | No | Accettata in chiaro, salvata crittografata |
| `email_from` | string | Si | Es. `"Ufficio Acquisti <acq@azienda.it>"` |
| `email_reply_to` | string | No | — |
| `unita_organizzativa_id` | int | No | NULL = account di sistema |
| `attivo` | bool | No | Default true. Booleano JSON, come sopra |

> **`codice_interno` (chiave logica immutabile)**: NON è un campo del payload. Alla
> create il backend lo valorizza automaticamente `= codice` e da lì resta **stabile
> e immutabile** (lockato a DB), mentre il `codice` può essere rinominato via PATCH.
> La logica di sistema (es. fallback account `SISTEMA` in `fn_resolve_email_account`)
> usa `codice_interno`, non il `codice` mutabile.

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

Body vuoto. Tenta login SMTP senza inviare email.

⚠️ **Non risponde OK a un account che non puo' spedire.** In `DEBUG` e' sempre
console mode e il test torna successo **per qualunque account** (non c'e' niente
da provare, e nemmeno un host reale viene contattato). **Fuori** da `DEBUG`, con
host vuoto o `smtp.example.com`, torna **`success: false`** con il motivo — prima
rispondeva OK, ed e' il verde che ha ingannato una persona.

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
2. Host vuoto o placeholder (`smtp.example.com`) → `can_test=True` anche senza
   password. ⚠️ Il pulsante resta **premibile di proposito**: dal 2026-09-11 il
   test dira' «SMTP non configurato» invece di OK, e spegnerlo qui toglierebbe a
   chi guarda l'unico modo di sentirselo dire.
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
| `search` | string | No | — | Ricerca libera: le colonne le decide il catalogo della lista `config.email_template`. Da un carattere (tabella di configurazione) |
| `codice` | string | No | — | Filtro esatto per codice |
| `limit` | int | No | 25 | Max 200 |
| `offset` | int | No | 0 | — |
| `order_by` | string | No | codice + lingua | Colonna di ordinamento |
| `order_dir` | string | No | `asc` | `asc` / `desc` |

Risposta paginata come la lista account (`count`, `page`, `page_size`, `total_pages`, `results`).

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
| `attivo` | bool | No | Default true. Booleano JSON, come sopra |

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
`unita_organizzativa_id`, `data_da`/`data_a` (`YYYY-MM-DD`, giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09), `data_a` incluso; malformate → 400), `limit`, `offset`,
`order_by` (default `data_insert`), `order_dir` (default `desc`). Risposta paginata
come le altre liste admin. `search`: le colonne le decide il catalogo della lista
`config.email_log`; sotto 3 caratteri il termine non filtra (e' un registro, non
configurazione — fino al 2026-09-24 filtrava da un carattere).

Il dettaglio include `corpo_inviato_html` e `corpo_inviato_testo` (corpo esattamente
come inviato, anche se la bozza e' stata modificata prima dell'invio).

---

## Endpoint Operatore — Outbox (Bozze Email)

Base path: `/api/v1/core/`
Autenticazione: JWT (`DomainAPIView`), area funzionale **`config`**: livello `LETTURA`
per le letture, `TUTTO` per preparare, modificare, spedire e gestire allegati. Le view
di bozze e allegati non dichiarano `skip_area_check`: non e' un'API aperta a ogni
operatore. Fanno eccezione solo le due letture del log (lista e lookup stati, §Endpoint
Operatore — Log Email), che dichiarano `skip_area_check`.

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
| `ambito` | string | **Si** | `SISTEMA`/`REPARTO`/`OPERATORE` — **nessun default** |
| `pratica_id` | int | No | Collegamento a pratica |
| `auth_user_id` | int | No | Operatore destinatario |

Regole sull'`ambito` (`E_EMAIL_OP`, 400):

- assente o fuori elenco → rifiutato: chi crea una bozza dichiara di che cosa e';
- diverso da `SISTEMA` → serve un'azienda attiva nel token: la bozza prende
  l'emittente **attivo** di chi la crea (per `SISTEMA` resta vuoto). Senza
  (modalita' «Tutti gli emittenti», di sola lettura) il rifiuto e'
  `E_EMITTENTE_NON_RISOLTO` (400), lo stesso di ordini e contratti: il rimedio
  e' scegliere l'azienda in alto;
- `REPARTO` → `unita_organizzativa_id` obbligatorio.

Risposta: bozza completa con oggetto/corpo pre-compilati (editabili dal frontend).

### Lista bozze

```http
GET /api/v1/core/email/outbox/
```

Il perimetro **non** e' un filtro della view: lo applica la RLS (§Ambito e
visibilita'). Una bozza `REPARTO` la vedono i colleghi del reparto, una
`OPERATORE` solo il suo autore. ⚠️ Fino al 2026-09-25 la view filtrava per
`creato_da_user_id` = chi chiede: era una seconda sede della regola, e
nascondeva ai colleghi le bozze di reparto.
Filtri: `stato`, `pratica_id`, `limit`, `offset`.

### Dettaglio / Modifica bozza

```http
GET   /api/v1/core/email/outbox/{id}/
PATCH /api/v1/core/email/outbox/{id}/
```

GET include lista allegati. PATCH accetta: `oggetto`, `corpo_html`, `corpo_testo`,
`destinatari_cc`, `destinatario`. Solo bozze DRAFT sono modificabili.

**Chi puo' accedere** lo decide la RLS, in lettura e in scrittura (§Ambito e
visibilita'): una bozza fuori perimetro non si legge, quindi esce come
inesistente. Dal 2026-09-25 non c'e' piu' un controllo di proprieta' nella view.
Bozza inesistente (o fuori perimetro) esce con `E_EMAIL_BOZZA_NOT_FOUND`, HTTP
**404**: le due cose escono uguali, di proposito, per non rivelare le bozze degli
altri. Una bozza che non e' piu' `DRAFT` (gia' partita, in partenza o annullata)
rifiuta modifica, invio e annullo con `E_EMAIL_NON_BOZZA` (409). Tutti i codici
in §«Codici d'errore».
### Conferma e invia

```http
POST /api/v1/core/email/outbox/{id}/send/
```

Transizione: DRAFT → READY → **SENT** (SMTP riuscito), → **DRAFT** (SMTP fallito,
l'operatore puo' riprovare) oppure → **SIMULATA** (console mode: la mail e' stata
mostrata, non spedita — dal 2026-09-11). Crea record in `email_log` con corpo dalla
bozza (non dal template originale). Copia allegati su `email_log_id`.

La riga di `email_log` porta l'**azienda** (`emittente_fiscale_id`) e l'**autore**
(`creato_da_user_id`) **della bozza**, non di chi preme «invia»: un super admin
che spedisce la bozza di un altro non ne diventa l'autore (D-5 di
brief-db-email-visibilita-per-ambito). Sono le due colonne su cui la RLS del log
decide chi rivede la mail. ⚠️ Fino al 2026-09-25 l'`INSERT` del log non scriveva
nessuna delle due: ogni invio di una bozza non di sistema veniva rifiutato dal
database.

La mail parte **con i suoi allegati** (messaggio `multipart/mixed`). Un file che
non si legge dallo storage fa fallire l'invio (`FAILED`, col motivo nel log):
una mail non parte senza l'allegato promesso. ⚠️ Fino al 2026-09-25 gli allegati
si salvavano e si agganciavano al log, ma la mail partiva senza. Il rilancio di
una mail fallita (`send_pending_emails`) rilegge gli allegati dal log.

Lo stato dell'invio e' nel log (`SENT`, `FAILED`, `SIMULATA`); lo stato outbox dice
se l'operatore deve agire (DRAFT = da riprovare, SENT = completato).
⛔ **La bozza segue l'esito della MAIL, non il valore di ritorno**: in console mode
`send_raw` torna `True` pur non avendo spedito niente, e scrivere `SENT` sarebbe la
stessa bugia una tabella piu' in la' — con le due righe legate da `email_log_id`.

**Semantica saga/outbox (fix analisi-fix-transazioni #16, 2026-07-08).** Lo stato
`READY` e' committato **prima** dell'invio SMTP (l'invio esterno sta fuori da ogni
transazione DB). I **tre write post-invio** (link outbox↔log + copia allegati + stato
finale `SENT`/`DRAFT`) sono ora fusi in **un solo** `transaction.atomic()`: o tutti o
nessuno. Se quel blocco fallisce, l'outbox resta `READY` **coerente** (non parziale):
nessun stato ibrido con log linkato e allegati mancanti. Un outbox rimasto `READY`
(bozza fantasma) e' recuperabile da un job di riconciliazione — **follow-up** da
progettare per NON ri-inviare (lo SMTP e' gia' partito): recupero idempotente, non
re-send.

L'account di invio si risolve **prima** di portare la bozza a `READY`: se nessun
account si risolve la chiamata fallisce con `E_EMAIL_ACCOUNT_NON_CONFIGURATO`
(500: manca la configurazione, chi invia non puo' rimediare) e la bozza **resta `DRAFT`**,
quindi si puo' riprovare o annullare. Fino al 2026-09-28 l'ordine era inverso e la
bozza restava `READY`, ne' rinviabile ne' annullabile (F-1 dell'
[analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).

### Annulla bozza

```http
POST /api/v1/core/email/outbox/{id}/cancel/
```

Transizione: DRAFT → CANCELLED. Toglie gli allegati: le righe di
`config.email_allegato` **prima** di scrivere `CANCELLED`, nella stessa
transazione (dopo, il database non le lascia piu' toccare), e i file dallo
storage **dopo** il commit. ⚠️ Fino al 2026-09-25 si cancellavano i soli file, e
le righe restavano a puntare a file inesistenti.

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

Solo su una bozza `DRAFT`: altrimenti `E_EMAIL_ALLEGATO_NON_BOZZA` (409), il
codice con cui la stessa regola la rifiuta il database — il controllo sta anche
qui perche' il file si scrive su disco **prima** dell'`INSERT`.

### Lista allegati

```http
GET /api/v1/core/email/outbox/{id}/allegati/list/
```

### Elimina allegato

```http
DELETE /api/v1/core/email/allegati/{allegato_id}/
```

Elimina file fisico + record DB. Solo su una bozza `DRAFT`: lo applica il
**database** (`config.trgfn_email_allegato_guard_solo_bozza`), che su una mail
spedita, in partenza o annullata — o su un allegato che sta solo nel log —
risponde `E_EMAIL_ALLEGATO_NON_BOZZA` (409) prima che il file venga toccato.
✅ Chiude il difetto F-2 (2026-09-25): all'invio la **stessa** riga viene legata
al log, e toglierla da una mail spedita la cancellava dalla sua storia.

### Download allegato

```http
GET /api/v1/core/email/allegati/{allegato_id}/download/
```

Ritorna `FileResponse` con `Content-Disposition: attachment`. Guard anti-path-traversal
su `file_path` (BB `percorso_allegato`, lo stesso dell'invio SMTP).

---

## Endpoint Operatore — Log Email

```http
GET /api/v1/core/email/log/
```

Il perimetro **non** e' un filtro della view: lo applica la RLS su
`config.email_log` per **ambito** ed **emittente** (§Ambito e visibilita'); in piu'
il processo `send_pending_emails` vede le mail del suo perimetro, per poterle
ritentare.
Filtri: `search`, `stato`, `pratica_id`, `data_da`/`data_a` (`YYYY-MM-DD`, giorni dell'azienda come sopra), `limit`
(default 25, max 200), `offset`, `order_by` (default `data_insert`), `order_dir` (assente: `desc`
sulle colonne data, `asc` sulle altre). Risposta `{"count", "results"}`. `search` e' la ricerca della lista `config.email_log` (stessa query): le
colonne le decide il suo catalogo, e sotto 3 caratteri il termine non filtra.

**Chi entra** (dal 2026-09-26, decisione di Tid): **ogni operatore** —
`skip_area_check`, nessuna `area_funzionale`. Chi vede quale mail lo decide la
RLS per ambito (sopra), e un livello d'area in piu' sarebbe una seconda regola
accanto a quella del modello. ⛔ Vale per questa sola lettura: le bozze e
l'invio restano sotto `config` finche' non esiste l'azione di processo
`invia_email`.

### Stati del log (lookup)

```http
GET /api/v1/core/email/log/stati/
```

Il vocabolario del filtro `stato`, stessa porta della lista. Risposta
`{"data": {"results": [{codice, descrizione, ordering}, ...]}}`, nell'ordine
dichiarato (`SENT` per primo). Sede: `email_constants.STATI_EMAIL_LOG_DESCRIZIONI`,
confrontata col `CHECK` `chk_email_log_stato` da
`core/tests/db/test_email_log_stati_guardrail.py`. ⚠️ Fino al 2026-09-26 stava
in `/amm-software/lookup/email-log-stati/` (solo super admin).

---

## Codici d'errore

Dal 2026-10-09 (brief-db-codici-non-trovato-email-e-permessi): i «non trovato»
e le condizioni di stato hanno un codice proprio; dal 2026-10-10 (R-7) anche il
template mancante, il percorso d'allegato fuori archivio e la mail piena.
`E_EMAIL_OP`, `E_OUTBOX` ed `E_EMAIL_ADMIN` restano per i soli **dati errati**
della richiesta (campo obbligatorio, chiave fuori contratto, tipo o dimensione
del file), HTTP 400.

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_EMAIL_BOZZA_NOT_FOUND` | 404 | bozza inesistente o fuori perimetro (dettaglio, modifica, invio, annullo, allegati) |
| `E_EMAIL_NON_BOZZA` | 409 | la mail non e' piu' in bozza: modifica, invio, annullo |
| `E_EMAIL_ALLEGATO_NON_BOZZA` | 409 | allegato aggiunto o tolto fuori bozza (codice del database) |
| `E_EMAIL_ALLEGATO_NOT_FOUND` | 404 | allegato inesistente o fuori perimetro (download, rimozione) |
| `E_EMAIL_ALLEGATO_FILE_MANCANTE` | 500 | la riga dell'allegato c'e', il file sullo storage no: guasto, non un «non trovato» |
| `E_EMAIL_ACCOUNT_NON_CONFIGURATO` | 500 | nessun account email da cui spedire |
| `E_EMAIL_TEMPLATE_NON_CONFIGURATO` | 500 | nessun template per l'invio, dopo il ripiego (mail di sistema e preparazione della bozza). Non e' `E_EMAIL_TEMPLATE_NOT_FOUND`: il codice del template lo sceglie il programma |
| `E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO` | 500 | il `file_path` dell'allegato (dal database) esce dall'archivio: dato alterato, caso da guardare anche per la sicurezza. Download e invio si fermano; la cancellazione lo scrive nel log e prosegue |
| `E_EMAIL_ALLEGATI_LIMITE` | 409 | la mail ha gia' il numero massimo di allegati |
| `E_EMITTENTE_NON_RISOLTO` | 400 | bozza non di sistema senza azienda attiva (modalita' «Tutti gli emittenti») |
| `E_EMAIL_ACCOUNT_NOT_FOUND` | 404 | admin: account inesistente (dettaglio, modifica, eliminazione, test) |
| `E_EMAIL_TEMPLATE_NOT_FOUND` | 404 | admin: template inesistente (dettaglio, modifica, eliminazione, anteprima) |
| `E_EMAIL_LOG_NOT_FOUND` | 404 | admin: riga del log inesistente o fuori perimetro |

⚠️ `E_EMAIL_LOG_NOT_FOUND` non e' `E_EMAIL_LOG_INESISTENTE` (500): quello nasce
nel database su un id che ha scritto il backend un istante prima; qui l'id lo
sceglie l'amministratore.

⭐ Una sede per lettura: la bozza la legge `EmailOutboxService.get_bozza` (i
verbi del service e le due letture senza verbo); le view che chiamano un verbo
**non** la rileggono prima. L'allegato passa da `_allegato_o_404`, account e
template da `_account_o_404` / `_template_o_404` della view admin.

---

## Risoluzione Account — Catena di Fallback

```text
Richiesta invio email (unita_organizzativa_id = 42)
  → fn_resolve_email_account(42)
  → 1. Account specifico del reparto 42 (attivo)
  → 2. Account di sistema (codice_interno = 'SISTEMA', attivo)
  → NULL se nessuno trovato → errore E_EMAIL_ACCOUNT_NON_CONFIGURATO (500)
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
  → NULL se nessuno trovato → errore E_EMAIL_TEMPLATE_NON_CONFIGURATO (500)
```

## Rendering Variabili

I template supportano variabili con sintassi `{{nome_variabile}}`.
Variabili non trovate nel dizionario restano invariate nel testo
(es. `{{link}}` rimane se `link` non e' tra le variabili).

## Ambito e Visibilita'

Ogni email (outbox e log) ha un campo `ambito`:

| Ambito | Significato | Visibilita' |
| --- | --- | --- |
| `SISTEMA` | Email infrastrutturali (inviti, reset) | Solo super admin |
| `REPARTO` | Email del reparto (comunicazioni a clienti/fornitori) | Operatori dell'unita' organizzativa + super admin |
| `OPERATORE` | Email personale dell'operatore | Solo l'autore (`creato_da_user_id`) + super admin |

⭐ **La regola la applica il database, dal 2026-09-25**: le policy RLS di
`config.email_log`, `config.email_outbox` e `config.email_allegato` passano tutte
da `script.fn_scope_email_ambito`, in lettura e in scrittura. Su `REPARTO` e
`OPERATORE` l'emittente della mail deve essere anche nel perimetro di chi guarda
(`AND`). Gli allegati si vedono se si vede la bozza o il log a cui appartengono.
Il backend non ne tiene una copia. Brief:
[brief-db-email-visibilita-per-ambito](../../../dev/work-done/brief-db-email-visibilita-per-ambito.md).

⚠️ `auth_user_id` **non** e' l'autore: e' l'utente **di cui la mail parla**
(l'operatore invitato, l'utente del reset password).

Email con `pratica_id` sono visibili anche dalla scheda pratica: ⏸ **regola del
modello non ancora applicata**, rimandata al cantiere della scheda pratica (D-3).

## Management Command

```bash
# Processa email in coda
python manage.py send_pending_emails

# Preview senza invio
python manage.py send_pending_emails --dry-run

# Limita a 10 email (default 50)
python manage.py send_pending_emails --limit 10
```

Che cosa sia «in coda» lo dice la vista `config.vw_email_in_coda`: le `PENDING`
sempre, piu' le `RETRY`/`FAILED` che hanno ancora tentativi e il cui prossimo
tentativo e' dovuto. Il command lo sveglia un timer systemd (`backend/deploy/sveglie.json`).
Per ogni email in coda, usa l'`email_account_id` originale (non risolve da zero).

## Sicurezza

- Password SMTP crittografata con Fernet (chiavi `DJANGO_FIELD_ENCRYPTION_KEYS`, separate dalla `SECRET_KEY`) — mai in chiaro in DB o API
- Guard su password NULL: `decrypt()` e `test_connection` gestiscono account senza password configurata
- Ownership check su tutte le operazioni outbox e allegati (fail-closed se nessun outbox padre)
- Path traversal guard su download allegati (`normpath` + `startswith`)
- Whitelist colonne aggiornabili nei metodi UPDATE del repository (previene SQL injection da kwargs)
- MIME type whitelist per upload allegati
- Template rendering sicuro: solo sostituzione `{{chiave}}`, nessuna esecuzione codice
- Outbox: stato riflette esito reale (SENT su successo, SIMULATA in console mode, DRAFT su fallimento SMTP)
- SMTP catch specifico: `(SMTPException, OSError, ValueError)` — errori di programmazione non mascherati
- Connessione SMTP chiusa in `finally` (no connection leak)

## Settings Django

| Setting | Default | Scopo |
| --- | --- | --- |
| `MAILERS['default']['BACKEND']` | `console` | Mailer Django (non usato dal service, che parla SMTP per-account). Sostituisce `EMAIL_BACKEND`, deprecato da Django 6.1 |
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
| `apps/core/services/email_allegati_storage.py` | Radice e percorso degli allegati su disco (guard path traversal) |
| `apps/amm_software/api/email_views.py` | API admin (account, template, log) |
| `apps/core/api/email_views.py` | API operatore (outbox, allegati, log) |
| `apps/core/management/commands/send_pending_emails.py` | Command coda email |
| `apps/core/api/constants.py` | DEFAULT_LIMIT, MAX_LIMIT condivisi |
