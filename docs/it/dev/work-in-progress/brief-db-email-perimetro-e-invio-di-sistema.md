# Brief — Il perimetro delle email, e come parte una email di sistema

> **Destinatario:** team DB (`dev/db-tid`) e backend.
>
> **Che cos'è.** L'**unico filo ancora aperto** del cantiere «nessun processo
> senza operatore». Tutto il resto è chiuso e archiviato in `work-done/`:
> l'analisi, il brief del disegno DB, gli otto residui e il piano BE/FE.
>
> ⭐ **Perché esce da lì.** Viveva nel §1-octies di un documento da 1.400 righe
> intitolato «gli otto residui», sette dei quali chiusi. Un filo vivo dentro un
> archivio non si legge: si perde.
>
> **Stato:** 🔴 **DUE PERCORSI SONO ROTTI ADESSO** (misurato su `dbdev`,
> 2026-09-05): il reset password e gli inviti fatti da chi non è super admin.
> È l'effetto della RLS accesa su `config.email_log` — attesa e voluta, ma la
> metà che la rende percorribile non c'è ancora.

---

## 1. La decisione, e non è più in discussione

✅ **Chi legge le email di ambito `SISTEMA`** (reset password, alert — il loro
contenuto vale quanto una credenziale):

| | |
| --- | --- |
| fra le **persone** | solo il **super admin** |
| fra le **macchine** | l'**identità tecnica del processo che spedisce** |

⭐ Nel database *portare è leggere*: non esiste un modo di spedire una riga senza
vederla. Il postino non ha titolo a leggere la lettera, e deve comunque portarla.

✅ **E la mail di sistema parte SUBITO** (decisione di Tid, 2026-09-05). Non si
accoda in attesa del giro successivo del worker: un reset password che arriva un
minuto dopo è un reset password che l'utente ha già chiesto due volte.

---

## 2. Che cosa c'è già, e funziona

| | |
| --- | --- |
| `config.email_log` | RLS **accesa**, policy che ramifica su `ambito` (`20260905-41`…`-44`) |
| `config.email_outbox` | idem (`20260905-32`, `-37`) |
| `config.fn_accoda_email_sistema` | `SECURITY DEFINER`, scrive **solo** `ambito='SISTEMA'` con emittente `NULL` — ⭐ non è parametrica apposta: non è una porta per aggirare la policy |
| `script.fn_scope_identita_processo` | il ramo che fa leggere le `SISTEMA` all'identità tecnica di `send_pending_emails` |
| lato BE | `ambito` non ha più default in nessuna firma; `create_outbox` valorizza l'emittente; `send_pending_emails` gira col roster, un'azienda alla volta |

---

## 3. 🔴 Che cosa è rotto, misurato

Chi riesce a scrivere una riga `SISTEMA` su `config.email_log`, oggi:

| percorso | esito |
| --- | --- |
| **nessuna sessione** — reset password (endpoint non autenticato) | ⛔ write-guard |
| **operatore non super admin** — invita un operatore o un utente portale | ⛔ policy |
| super admin | ✅ |
| identità tecnica di `send_pending_emails` | ✅ |
| `config.fn_accoda_email_sistema` senza sessione | ✅ |

⇒ **Reset password e inviti non funzionano.** Il rimedio esiste a metà.

---

## 4. Che cosa serve dal DB

### 4.1 ⛔ La metà mancante: l'invio, non solo l'accodamento

`fn_accoda_email_sistema` si chiama **accoda** e scrive `stato = 'PENDING'`. Ma la
decisione del §1 è che la mail **parta subito**: il backend, dopo aver scritto la
riga, tenta l'invio e poi deve **aggiornarne lo stato** (`SENT` / `FAILED`,
`tentativi`, `inviato_at`).

⛔ Quell'`UPDATE` è bloccato dalla stessa policy, per lo stesso motivo: chi
spedisce un reset password non ha una sessione.

**Che cosa serve.** Un modo, per il percorso senza sessione, di **chiudere** la
riga che ha appena scritto — l'esito dell'invio che ha appena tentato.

⚠️ **E non deve diventare una porta di servizio**: il pregio di
`fn_accoda_email_sistema` è che sa scrivere una cosa sola. La sua gemella
dovrebbe poter toccare **solo** una riga `SISTEMA` e **solo** i campi dell'esito.
La forma la decidete voi.

### 4.2 ⚠️ La funzione perde tre colonne che i chiamanti passano

`fn_accoda_email_sistema` non accetta `unita_organizzativa_id`,
`destinatari_cc`, `pratica_id`. Misurato: **tutti e tre** i chiamanti di sistema
passano `unita_organizzativa_id` (reset password × 2, invito operatore, invito
portale).

⇒ Instradando lì senza allargarla, quell'informazione **si perde in silenzio**
sulle email di sistema — che è peggio di un errore. O la funzione le accetta, o
si dichiara che su una `SISTEMA` non servono e si toglie dai chiamanti.

---

## 5. Che cosa fa il backend, quando arriva

Un punto solo — `EmailRepository.create_log` — instrada su
`fn_accoda_email_sistema` quando `ambito = 'SISTEMA'`, e `update_log_stato` sulla
gemella dell'esito. ⭐ Tutti e quattro i chiamanti passano di lì: non si tocca
nessuna delle quattro chiamate.

⚠️ Da fare **insieme** al §4.1: instradare solo l'`INSERT` sposterebbe la
rottura di due righe più in là, sull'`UPDATE`.

---

## 6. Da dove viene

Tutti in `work-done/`, archiviati il 2026-09-05:

* `analisi-db-be-processi-automatici-identita-e-perimetro.md` — le decisioni e il perché
* `brief-db-processi-automatici-identita-e-perimetro.md` — il disegno DB, sette fasi
* `brief-db-processi-automatici-residui-be.md` — gli otto residui: questo filo era il §1-octies
* `brief-db-storicizzazione-bersagli-spariti.md` — R-12, il job fermo da sei mesi
* `piano-be-fe-processi-automatici-identita-e-perimetro.md` — i lotti BE/FE
