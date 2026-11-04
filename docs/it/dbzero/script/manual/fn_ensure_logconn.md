## 📘 Documentazione Concettuale – Funzione `script.fn_ensure_logconn`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa) — la regola unica: se il canale è acceso, e con quale stringa
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — registra un errore fuori transazione, e la chiama
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) — genera il `tx_id` sulla connessione che questa apre
> * [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure) — il verbale di un job fallito, sulla stessa connessione
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva, passando da `fn_log_error_only`
>
> Guide:
>
> * [dblink](/postgresql/dblink) — il canale dei registri fuori transazione: come è fatto

---

### 🎯 Scopo Principale

Apre la connessione `dblink` persistente di nome **`logconn`** verso il canale di log, se il canale è
acceso e la connessione non è già aperta. Su quella connessione i registri fuori transazione
scrivono righe che sopravvivono all'annullamento della transazione di chi le scrive.

---

### Come funziona

1. **Il canale.** Se è acceso, e con quale stringa di connessione, lo dice
   [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa). Spento o non
   configurato: la funzione esce senza fare niente.
2. **Già aperta?** Se `logconn` è già fra le connessioni della sessione, non si riconnette.
3. **L'apertura.** Altrimenti apre `logconn` con la stringa del canale. La connessione resta aperta
   fino alla fine della sessione, o fino a un `dblink_disconnect('logconn')`.

Chiamarla più volte non apre più connessioni: è idempotente.

---

### ⛔ Non solleva mai

Il canale di log è un **servizio**, non una precondizione delle scritture. Qualunque errore
nell'apertura — servizio o credenziali sbagliati, server irraggiungibile, troppe connessioni —
diventa un `WARNING` con lo SQLSTATE, e la funzione ritorna normalmente. Una connessione già aperta
da un'altra chiamata nello stesso istante si ignora in silenzio.

⚠️ Il rovescio: dal fatto che la chiamata «non è esplosa» non si sa se la connessione c'è. Chi deve
saperlo guarda `dblink_get_connections()` subito dopo, come fanno tutti i suoi chiamanti.

---

### ⚠️ È di `postgres`

È `SECURITY INVOKER` con proprietario `postgres`, dichiarato nel registro dei proprietari delle
funzioni, e la chiamano funzioni `SECURITY DEFINER` di `postgres`: `dblink` rifiuta a chi non è
superuser una connessione senza password. Il percorso di ricerca è fissato nella definizione
(`pg_catalog`, `public`, `pg_temp`; `public` serve perché `dblink` vive lì).

Un `CREATE OR REPLACE` dal ruolo di migrazione fallisce, perché la funzione non è sua: per
modificarla si prende in prestito la proprietà con `dbops.fn_sync_functions_owner`, si sostituisce la
funzione e la si restituisce, nello stesso changeSet.

---

### Test

* `db/pgtap/script/test-canale-log-v1.sql` — test 7: con un canale irraggiungibile la funzione non
  solleva. Test 16: non legge da sé i parametri del canale (presidio sul testo).

---

### Note di migrazione

* 2025-08-13 — ultima revisione dell'albero `migrations/`: apre `logconn` dalla sola
  `myapp.dblink_log_connection` e assorbe solo la connessione già aperta e il troppo-connessioni.
* 2026-11-04 — il canale lo dice `script.fn_canale_log_stringa` (D26 di `brief-db-revisione-dbops`):
  prima leggeva da sé l'interruttore (assente = acceso, ma il vuoto = spento) e ignorava
  `myapp.logconn`. Ogni errore di connessione diventa un `WARNING` (D1): prima un canale
  irraggiungibile faceva fallire, attraverso il `tx_id`, ogni scrittura su una tabella tracciata.
  Il commento, che nominava un parametro inesistente (`dblink.log_connection`), è riscritto.

---

{% include-markdown "signature-core.md" %}
