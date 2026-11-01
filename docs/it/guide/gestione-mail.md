# Guida – Gestione Mail

> **Ultimo aggiornamento**: 1 novembre 2026
>
> Destinatari: amministratori di sistema, sviluppatori backend, analisti funzionali
>
> Vedi anche
>
> * [Guida Risorse Umane e Accessi](/guide/risorse-umane-e-accessi)
> * [Guida Gestione Pratiche](/guide/gestione-pratiche)
> * [API Email (doc backend)](/backend/core/manual/api_email)
> * [API Invito Operatore](/backend/core/manual/api_invito_operatore)
> * [API Reset Password](/backend/core/manual/api_password_reset)

---

## Introduzione

Zero ERP integra un sistema di invio email pensato per coprire le esigenze operative
di un ERP in produzione, senza diventare un client di posta. L'email e' un **canale di uscita**:
il sistema compone, invia e traccia le comunicazioni, ma non riceve email ne' gestisce
caselle di posta in ingresso.

Ogni reparto (unita' organizzativa) puo' avere il proprio account SMTP e i propri template
personalizzati. Il sistema risolve automaticamente quale account e quale template usare
in base al contesto, con fallback sull'account di sistema.

**Cosa troverai in questa guida:**

* Come funziona il modello email (account, template, outbox, log)
* Come configurare un account SMTP per reparto o per il sistema
* Come personalizzare i template email (variabili, override per reparto/tipo pratica)
* La modalita' console per sviluppo (senza SMTP reale)
* I confini architetturali: cosa il sistema fa e cosa no
* Come configurare Gmail per test reali

---

## Tabelle coinvolte

* [config.email_account](/dbzero/config/tabelle/email_account) — account SMTP per reparto
* [config.email_template](/dbzero/config/tabelle/email_template) — template parametrizzabili
* [config.email_log](/dbzero/config/tabelle/email_log) — log immutabile di ogni invio
* [config.email_outbox](/dbzero/config/tabelle/email_outbox) — bozze editabili prima dell'invio
* [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — `send_pending_emails` è un lavoro **di dominio**: gira per conto di un'azienda, non in incognito
* [config.email_allegato](/dbzero/config/tabelle/email_allegato) — allegati per outbox e log
* [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative) — reparti

Funzioni:

* `config.fn_resolve_email_account(uo_id)` — risolve account SMTP con fallback
* `config.fn_resolve_email_template(codice, uo_id, tipo_prest_id, lingua)` — risolve template con fallback 5 livelli

---

## Come funziona

### Il flusso di invio

```
1. Qualcosa nel sistema chiede di inviare un'email
   (invito operatore, reset password, notifica pratica, comunicazione manuale)
   |
2. EmailDispatchService risolve l'account SMTP:
   → cerca account del reparto dell'operatore
   → se non trovato, usa account SISTEMA (fallback)
   |
3. Risolve il template email:
   → cerca template per reparto + tipo pratica + lingua
   → fallback progressivo fino al template di sistema in italiano
   |
4. Renderizza oggetto e corpo sostituendo le variabili {{...}}
   |
5. Crea record in email_log con stato PENDING
   |
6. Invia via SMTP (o logga in console se in modalita' sviluppo)
   |
7. Aggiorna stato: **SENT** (spedita), **FAILED** (non spedita) o **SIMULATA**
   (mostrata a video invece che spedita — modalita' console, dal 2026-09-11)
```

### Invio diretto vs bozza (outbox)

Il sistema supporta due modalita':

**Invio diretto** — usato per email automatiche (inviti, reset, notifiche SLA):

* `EmailDispatchService.send_email()` → risolve, renderizza, invia in un passo
* L'operatore non vede la bozza, l'email parte automaticamente

**Bozza editabile** — usato per comunicazioni manuali (da pratica, da reparto):

* `EmailOutboxService.prepare_draft()` → crea bozza con corpo pre-compilato
* L'operatore puo' modificare oggetto, corpo, destinatari, allegati
* Alla conferma: `confirm_and_send()` → crea log + invia
* Se l'invio fallisce, la bozza torna a DRAFT e l'operatore puo' riprovare

---

## Configurare un account SMTP

### Account di sistema (obbligatorio)

Il seed iniziale crea un account con codice `SISTEMA` e host placeholder.
Per inviare email realmente, l'amministratore deve configurare un account SMTP valido.

Da **Amm. Software → Account Email** (solo ADMIN):

| Campo | Esempio | Note |
| --- | --- | --- |
| Codice | `SISTEMA` | Non modificare — e' il fallback di tutto il sistema |
| Descrizione | Account di sistema | Libero |
| SMTP Host | `smtp.gmail.com` | ⚠️ Vuoto o `smtp.example.com` = l'account **non spedisce**: e' modalita' console solo in sviluppo, altrove e' configurazione che manca |
| SMTP Port | `587` | 587 per STARTTLS, 465 per SSL |
| SMTP TLS | `true` | Abilitare per Gmail e la maggior parte dei provider |
| SMTP SSL | `false` | Alternativo a TLS (non entrambi) |
| SMTP Username | `utente@gmail.com` | Credenziali del provider |
| SMTP Password | `xxxx-xxxx-xxxx-xxxx` | Accettata in chiaro, salvata crittografata (Fernet) |
| Email From | `ZeroErp <utente@gmail.com>` | Indirizzo mittente visibile al destinatario |
| Reply-To | (opzionale) | Se diverso da Email From |
| Unita' Organizzativa | (vuoto) | NULL = account di sistema |
| Attivo | `true` | |

### Account per reparto (opzionale)

Per far partire le email di un reparto con il proprio indirizzo mittente:

1. Creare un nuovo account in **Amm. Software → Account Email**
2. Associare il campo **Unita' Organizzativa** al reparto desiderato
3. Configurare le credenziali SMTP del reparto

Quando il sistema invia un'email nel contesto di quel reparto, usa l'account
del reparto. Se non ne trova uno, ricade sull'account SISTEMA.

### Esempio con Gmail (per sviluppo e test)

1. Abilitare 2FA sull'account Google
2. Generare una **App Password**: myaccount.google.com → Sicurezza → Password per le app
3. Configurare l'account SISTEMA:

| Campo | Valore |
| --- | --- |
| SMTP Host | `smtp.gmail.com` |
| SMTP Port | `587` |
| SMTP TLS | `true` |
| SMTP SSL | `false` |
| SMTP Username | `tuaemail@gmail.com` |
| SMTP Password | La App Password 16 caratteri |
| Email From | `ZeroErp Dev <tuaemail@gmail.com>` |

Limiti Gmail: 500 email/giorno, sufficiente per sviluppo e test.
Per produzione: valutare servizio dedicato (SendGrid, Mailgun, Amazon SES, SMTP aziendale).

### Modalita' console (sviluppo)

Quando `DEBUG = True` le email **non vengono inviate** ma loggate nel terminale
Django. ⚠️ Basta `DEBUG`: l'host non c'entra — anche con un SMTP reale
configurato, in sviluppo non parte niente.

```
============================================================
EMAIL (console mode)
============================================================
Da:       ZeroErp <test@example.com>
A:        mario@azienda.it
CC:       (nessuno)
Oggetto:  Benvenuto Mario in ZeroErp
------------------------------------------------------------
Benvenuto Mario! Sei stato invitato ad accedere...
============================================================
```

Il record viene comunque creato in `email_log`, cosi' si verifica il flusso
completo senza SMTP reale — ma con stato **`SIMULATA`** e `inviato_at` **vuoto**.

⛔ **Fino al 2026-09-11 quello stato era `SENT`**, ed era un difetto vero: una
mail stampata a video risultava *consegnata*, indistinguibile da una vera.
Nessun errore, nessun allarme — la si scopriva solo non vedendo arrivare niente.

### ⛔ E se `DEBUG = False` con l'host ancora finto?

Non e' console mode: e' **configurazione che manca**, e il programma lo dice.
L'email **non viene ne' spedita ne' stampata**, e il giornale registra
**`FAILED`** col motivo e la strada per rimediare. ⚠️ Anche il pulsante «prova
connessione» risponde di no: prima diceva OK, ed e' cosi' che un'installazione
e' rimasta senza posta senza che nessuno se ne accorgesse.

### Testare la connessione

Da **Amm. Software → Account Email**, bottone **Test** sull'account:

* Tenta login SMTP senza inviare email
* Ritorna successo/errore con dettaglio
* In modalita' console ritorna direttamente "Nessun test necessario"

---

## Personalizzare i template email

### Template di sistema (seed)

Il seed iniziale crea 4 template in italiano:

| Codice | Scopo | Variabili |
| --- | --- | --- |
| `INVITO_OPERATORE` | Email di invito al primo accesso | `nome`, `cognome`, `azienda`, `link`, `scadenza_ore`, `invitato_da` |
| `RESET_PASSWORD` | Email per reset password dimenticata | `nome`, `azienda`, `link`, `scadenza_ore` |
| `CAMBIO_PASSWORD_CONFERMA` | Notifica cambio password avvenuto | `nome`, `azienda`, `data_cambio` |
| `NOTIFICA_GENERICA` | Template generico per notifiche | `oggetto_custom`, `corpo_custom` |

### Variabili template

I template usano la sintassi `{{nome_variabile}}`. Le variabili vengono sostituite
al momento dell'invio con i valori forniti dal codice chiamante.

Esempio template:

```html
<h2>Benvenuto {{nome}} {{cognome}}!</h2>
<p>Sei stato invitato ad accedere al sistema <strong>{{azienda}}</strong>.</p>
<p>Clicca sul link seguente per attivare il tuo account:</p>
<p><a href="{{link}}">Attiva il tuo account</a></p>
<p>Il link scade tra {{scadenza_ore}} ore.</p>
```

Se una variabile non viene fornita, resta invariata nel testo (es. `{{link}}`
rimane se `link` non e' tra le variabili).

### Modificare un template esistente

Da **Amm. Software → Template Email** (solo ADMIN):

1. Selezionare il template dalla lista
2. Modificare **Oggetto**, **Corpo HTML** e/o **Corpo Testo**
3. Le variabili disponibili sono indicate nel campo `variabili_disponibili`
4. Usare il bottone **Preview** per verificare il risultato con dati di esempio

### Creare un override per reparto

Per far si' che il reparto Acquisti invii un testo diverso dal reparto Commerciale
per la stessa azione:

1. Creare un **nuovo template** con lo stesso codice (es. `INVITO_OPERATORE`)
2. Associare il campo **Unita' Organizzativa** al reparto Acquisti
3. Il sistema usera' automaticamente questo template quando l'email parte
   nel contesto del reparto Acquisti

Il template di sistema (senza reparto) resta il fallback per tutti gli altri reparti.

### Creare un override per tipo pratica

Per testi diversi in base al tipo di pratica (es. Reclamo vs Offerta):

1. Creare un template con lo stesso codice
2. Associare il campo **Tipo Prestazione** al tipo desiderato
3. Opzionalmente associare anche il reparto per un override ancora piu' specifico

### Catena di risoluzione (5 livelli)

Quando il sistema cerca un template, prova nell'ordine:

```
1. Reparto + Tipo pratica + Lingua richiesta
2. Reparto + Lingua richiesta (senza tipo pratica)
3. Sistema + Tipo pratica + Lingua richiesta
4. Sistema + Lingua richiesta (senza tipo pratica)
5. Sistema + Lingua italiana (fallback finale)
```

Il primo template trovato e attivo viene utilizzato. Se nessuno viene trovato,
l'invio fallisce con errore.

---

## Ambito e visibilita'

Ogni email (bozza e log) ha un **ambito** che determina chi puo' vederla:

| Ambito | Significato | Chi vede |
| --- | --- | --- |
| **SISTEMA** | Email infrastrutturali (inviti, reset, notifiche automatiche) | Solo ADMIN |
| **REPARTO** | Email del reparto (comunicazioni a clienti/fornitori) | Operatori dell'unita' organizzativa + ADMIN |
| **OPERATORE** | Email personale dell'operatore | Solo il creatore + ADMIN |

Le email collegate a una **pratica** (`pratica_id`) sono visibili anche dalla
scheda pratica, indipendentemente dall'ambito. Questo permette di ricostruire
la storia comunicativa di una pratica.

### ⭐ Dal 06-09-2026 questa tabella non è più solo una regola dell'applicazione

Fino a settembre l'ambito era una convenzione: a farlo rispettare era il codice
che leggeva le email. Ora lo fa **il database**, su tutte e due le tabelle — le
bozze e il registro degli invii.

Cambia poco per chi legge la tabella qui sopra, e cambia molto per chi scrive
codice: non c'è più modo di dimenticarsi il filtro.

⚠️ **E si aggiunge una seconda dimensione: l'azienda.** Le email che non sono di
sistema appartengono a un'azienda, e si vedono solo se quell'azienda è fra
quelle di chi guarda. Prima l'ambito diceva *quale gruppo di persone*; adesso
dice anche *di chi è la posta*.

⛔ Le email di **sistema** (reset password, inviti, alert) restano fuori da
questa seconda regola, ed è voluto: non appartengono a nessuna azienda, e il
loro contenuto vale quanto una password. Le legge solo un amministratore.

### ⚠️ La porta per i percorsi senza utente

Un reset password parte **prima** che qualcuno abbia fatto l'accesso: in quel
momento non c'è nessun utente in sessione. Con il filtro acceso, la scrittura
dell'email verrebbe rifiutata — cioè il reset non partirebbe, e nessuno se ne
accorgerebbe.

Per questo esistono due funzioni dedicate, ed è l'unico modo previsto di
scrivere una email di sistema da un percorso non autenticato:
[fn_accoda_email_sistema](/dbzero/config/funzioni/fn_accoda_email_sistema) la
mette in coda, [fn_chiudi_email_sistema](/dbzero/config/funzioni/fn_chiudi_email_sistema)
ne registra l'esito.

⛔ Non sono una scorciatoia da usare altrove: fanno una cosa sola, e solo per le
email di sistema.

---

## Allegati

Le bozze email supportano allegati caricati dall'operatore:

| Regola | Valore default | Configurabile |
| --- | --- | --- |
| MIME types ammessi | PDF, DOCX, XLSX, XLS, DOC, JPEG, PNG, GIF, TXT, CSV | `ALLOWED_MIME_TYPES` nel codice |
| Dimensione massima per allegato | 10 MB | `EMAIL_ATTACHMENT_MAX_SIZE_MB` in settings |
| Numero massimo per email | 10 | `EMAIL_ATTACHMENT_MAX_COUNT` in settings |

Gli allegati sono salvati su filesystem in `{EMAIL_ATTACHMENTS_ROOT}/{anno}/{mese}/{uuid}.{ext}`.
Quando un'email viene inviata, gli allegati vengono collegati anche al record log
per consultazione storica.

---

## Coda email e retry

Le email in coda (stato `PENDING` o `FAILED` con tentativi residui) vengono
processate dal management command:

```bash
# Processa email in coda
python manage.py send_pending_emails

# Preview senza invio
python manage.py send_pending_emails --dry-run

# Limita a 10 email per esecuzione
python manage.py send_pending_emails --limit 10
```

Schedulabile come cron job (pgAgent o crontab). Per ogni email il command
usa l'account SMTP originale (quello con cui l'email era stata preparata).

---

## Sicurezza

* **Filtro nel database** su bozze e registro invii: l'ambito e l'azienda non sono più solo una regola applicativa — vedi [Ambito e visibilità](#ambito-e-visibilita)
* **Password SMTP crittografata** con Fernet (chiavi `DJANGO_FIELD_ENCRYPTION_KEYS`, separate dalla `SECRET_KEY`) — mai in chiaro in DB o API
* **Ownership check** su tutte le operazioni outbox e allegati — fail-closed se nessun outbox padre
* **Path traversal guard** su download allegati
* **Whitelist colonne** aggiornabili nei metodi UPDATE del repository
* **Connessione SMTP** chiusa in `finally` (no connection leak)
* **Catch specifico** `(SMTPException, OSError, ValueError)` — errori di programmazione non mascherati

---

## Confini del sistema — cosa costruiamo e cosa no

### Cosa fa il sistema

| # | Funzionalita' | Esempio |
| --- | --- | --- |
| 1 | Email transazionali di sistema | Invito operatore, reset password, conferma |
| 2 | Notifiche operative | Pratica scaduta, SLA in allarme |
| 3 | Log completo di ogni invio | Corpo esatto inviato, allegati, esito |
| 4 | Template per reparto/tipo pratica | Testi diversi per "Reclamo Acquisti" vs "Offerta Commerciale" |
| 5 | Comunicazioni ad-hoc da pratica | Operatore scrive al cliente con anteprima |
| 6 | Storico comunicativo della pratica | Dalla pratica si vedono tutte le email |
| 7 | Allegati | Documenti inviati insieme alla email |

### Cosa NON fa il sistema (e perche')

| Escluso | Motivazione |
| --- | --- |
| Casella di posta in ingresso | Complessita' enorme (IMAP, spam, dedup) per risultato mediocre vs strumenti dedicati |
| Thread di conversazione | Richiede matching In-Reply-To/References — logica di un mail client |
| Ricezione email e associazione a pratiche | Territorio CRM/ticketing (NLP, regole matching) |
| Gestione completa CRM via email | Zammad, FreeScout, Chatwoot fanno questo con anni di maturita' |

### Strategia futura: integrazione via API

L'architettura lascia la porta aperta: `pratica_id` e `ambito` sulle email permettono
a un sistema esterno (CRM/ticketing) di correlare le proprie conversazioni con le
pratiche ZeroErp via API bidirezionale.

---

## Settings Django

| Setting | Default | Scopo |
| --- | --- | --- |
| `MAILERS['default']['BACKEND']` | `console` | Mailer Django (non usato dal service, che parla SMTP per-account). Sostituisce `EMAIL_BACKEND`, deprecato da Django 6.1 |
| `EMAIL_ATTACHMENTS_ROOT` | `{BASE_DIR}/email_attachments` | Root storage allegati |
| `EMAIL_ATTACHMENT_MAX_SIZE_MB` | `10` | Dimensione massima allegato in MB |
| `EMAIL_ATTACHMENT_MAX_COUNT` | `10` | Numero massimo allegati per email |
| `FRONTEND_URL` | obbligatoria, nessun default (l'ingresso Nginx, es. `https://backend-dev.tailXXXX.ts.net`) | Base URL per link nelle email (reset, invito, attivazione) |

---

## Endpoint API

### Admin (Amm. Software)

| Metodo | Endpoint | Scopo |
| --- | --- | --- |
| GET/POST | `/api/v1/amm-software/email-accounts/` | Lista e crea account SMTP |
| GET/PATCH/DELETE | `/api/v1/amm-software/email-accounts/{id}/` | Dettaglio, modifica, elimina |
| POST | `/api/v1/amm-software/email-accounts/{id}/test/` | Test connessione SMTP |
| GET/POST | `/api/v1/amm-software/email-templates/` | Lista e crea template |
| GET/PATCH/DELETE | `/api/v1/amm-software/email-templates/{id}/` | Dettaglio, modifica, elimina |
| POST | `/api/v1/amm-software/email-templates/{id}/preview/` | Preview template renderizzato |
| GET | `/api/v1/amm-software/email-log/` | Consultazione log (admin vede tutto) |
| GET | `/api/v1/amm-software/email-log/{id}/` | Dettaglio email inviata |

### Operatore

| Metodo | Endpoint | Scopo |
| --- | --- | --- |
| POST | `/api/v1/core/email/prepare/` | Prepara bozza da template |
| GET | `/api/v1/core/email/outbox/` | Lista bozze |
| GET/PATCH | `/api/v1/core/email/outbox/{id}/` | Dettaglio e modifica bozza |
| POST | `/api/v1/core/email/outbox/{id}/send/` | Conferma e invia |
| POST | `/api/v1/core/email/outbox/{id}/cancel/` | Annulla bozza |
| POST | `/api/v1/core/email/outbox/{id}/allegati/` | Upload allegato |
| GET | `/api/v1/core/email/outbox/{id}/allegati/list/` | Lista allegati |
| DELETE | `/api/v1/core/email/allegati/{id}/` | Elimina allegato |
| GET | `/api/v1/core/email/allegati/{id}/download/` | Download allegato |
| GET | `/api/v1/core/email/log/` | Consultazione log operatore |

---

## File Python

| File | Scopo |
| --- | --- |
| `apps/core/services/crypto_service.py` | Fernet encrypt/decrypt per password SMTP |
| `apps/core/db/email_repository.py` | Repository: CRUD 5 tabelle + fn_resolve |
| `apps/core/services/email_service.py` | EmailDispatchService: resolve, render, send |
| `apps/core/services/email_outbox_service.py` | EmailOutboxService: bozze, allegati, conferma |
| `apps/amm_software/api/email_views.py` | API admin (account, template, log) |
| `apps/core/api/email_views.py` | API operatore (outbox, allegati, log) |
| `apps/core/management/commands/send_pending_emails.py` | Command coda email |

---
{% include-markdown "signature-core.md" %}
