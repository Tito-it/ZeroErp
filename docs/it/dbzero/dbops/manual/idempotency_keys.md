## 📘 Documentazione Concettuale – Tabella `dbops.idempotency_keys`

> 👀 **Vedi anche**
>
> [dbops.fn_idempotency_prenota](/dbzero/dbops/funzioni/fn_idempotency_prenota) — la prenotazione di una key
> [dbops.request_log](/dbzero/dbops/manual/request_log) — correlazione via `idempotency_key`
> [dbops.error_log](/dbzero/dbops/tabelle/error_log)

La tabella **`dbops.idempotency_keys`** ricorda le **Idempotency-Key** che il client manda
con un'operazione che non si deve eseguire due volte (una fatturazione, una numerazione,
la registrazione di una distinta). Se la stessa richiesta arriva di nuovo, per esempio
perché l'operatore ha cliccato due volte o la rete ha ripetuto l'invio, il server non la
riesegue: rimanda la risposta della prima.

---

### 🎯 Scopo

* Evitare che un reinvio esegua di nuovo un'operazione irreversibile.
* Rimandare **la stessa risposta** a chi ripete la stessa richiesta.
* Rispondere «ancora in corso» a chi la ripete mentre la prima sta lavorando.

---

### Significato dei campi

* **`idempotency_key`**: la chiave mandata dal client (chiave primaria).
* **`status`**: `in_progress` (prenotata, l'operazione sta lavorando), `completed`
  (fatta), `failed` (fallita: si può riprovare con la stessa key).
* **`response_payload`**: la risposta da rimandare. C'è **se e solo se** la key è
  `completed`.
* **`auth_user_id`**, **`endpoint`**: chi ha prenotato la key e su quale richiesta
  (metodo e percorso). La risposta si rimanda solo allo stesso utente sullo stesso
  endpoint. `endpoint` è obbligatorio: ogni key è legata alla richiesta che l'ha
  prenotata. `auth_user_id` è vuoto per una richiesta anonima.
* **`prenotata_at`**: quando la key è stata prenotata o ripresa. Da qui si misura se
  una key `in_progress` è stata abbandonata.
* **`tx_id`**: la transazione DB dell'operazione completata.
* **`cleanup_at`**: quando la riga si può cancellare (un giorno dopo la nascita).

---

### Come funziona

1. Il backend chiama **[`dbops.fn_idempotency_prenota`](/dbzero/dbops/funzioni/fn_idempotency_prenota)**
   con la key, l'utente, l'endpoint e una dichiarazione obbligatoria: **la ripresa è
   ammessa?** (vedi il punto 2). La funzione risponde:
    * **ESEGUI** — la key è nuova, oppure era fallita, oppure era «in corso» da più di
      `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` (120 secondi, sopra il timeout del server
      web) **e la ripresa è ammessa**: chi lavorava è morto senza finire, e si riprende;
    * **REPLAY** — l'operazione è già stata fatta: il backend rimanda la risposta salvata;
    * **IN_CORSO** — la sta eseguendo un'altra richiesta, oppure è «in corso» oltre la
      soglia ma la ripresa **non** è ammessa: il backend risponde 409
      `E_IDEMPOTENCY_IN_PROGRESS` («L'operazione è ancora in corso»).
2. A operazione finita il backend scrive `completed` con la risposta. Qui le operazioni
   sono di due tipi, e il backend dice quale a ogni richiesta:
    * **in un passo solo**: `completed` si scrive **nella stessa transazione
      dell'operazione**, quindi o sono avvenute tutte e due, o nessuna. Una key rimasta
      «in corso» vuol dire che l'operazione non ha salvato niente: riprenderla è sicuro,
      e la ripresa è **ammessa**;
    * **a passi** (per esempio la pipeline di un lotto, che salva ogni passo per conto
      suo): una key rimasta «in corso» può coprire un lavoro già salvato in parte.
      Riprenderla lo rifarebbe, quindi la ripresa **non è ammessa**: la key resta «in
      corso» finché scade, o finché il frontend ne genera una nuova per il gesto dopo.
3. Se l'operazione fallisce, il backend scrive `failed`. Una key `failed` si riprende
   sempre, anche quando la ripresa non è ammessa: l'esito l'ha scritto il backend, quindi
   si sa che cosa è successo.

Una key usata da un **altro utente** o su un **altro endpoint** non rimanda niente: la
funzione risponde `E_IDEMPOTENCY_KEY_RIUSATA` (400), perché la risposta salvata è
dell'operazione di qualcun altro.

---

### Regole

* `status` ammette solo `in_progress`, `completed`, `failed`.
* Una key `completed` ha sempre `tx_id` e risposta; una key non `completed` non ha risposta.
* `endpoint` c'è sempre e non è vuoto.

---

### 🧹 Scadenza

Una key serve solo finché il client può rimandare la **stessa** richiesta: il frontend la
tiene per un gesto, al massimo dieci minuti. Per questo la riga vive **un giorno**: la
scadenza la scrive il trigger alla nascita, dalla regola id=24, e il job settimanale
cancella le righe scadute. Il dettaglio sta nella guida
[Audit e tracciabilità](/guide/audit-e-tracciabilita), sezione «Manutenzione e
retention».
