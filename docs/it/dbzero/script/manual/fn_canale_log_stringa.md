## 📘 Documentazione Concettuale – Funzione `script.fn_canale_log_stringa`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — apre la connessione di log, se questa funzione dice che il canale è acceso
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) — genera il `tx_id` sul canale, o ripiega sulla sentinella
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — registra un errore fuori transazione
> * [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure) — scrive il verbale di un job fallito fuori transazione
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — l'audit, che per ora legge l'interruttore a modo suo
>
> Guide:
>
> * [dblink](/postgresql/dblink) — il canale dei registri fuori transazione: come è fatto, come si spegne
> * [Parametri personalizzati (GUC)](/postgresql/parametri-personalizzati-(GUC)) — i tre parametri del canale: chi li imposta

---

### 🎯 Scopo Principale

Dice se il **canale di log fuori transazione** (la connessione `dblink` dei registri) è acceso, e
con quale stringa di connessione: restituisce la stringa se il canale è acceso, `NULL` se è spento
o non configurato. È la regola unica per chi deve scrivere sul canale.

---

### ⭐ La regola

Il canale è **acceso** se valgono insieme due cose:

1. **c'è una stringa di connessione non vuota**: `myapp.logconn` se è valorizzato, altrimenti
   `myapp.dblink_log_connection`. Una stringa di soli spazi conta come vuota;
2. **l'interruttore `myapp.log_with_dblink` non vale `off`**. Maiuscole e spazi non contano
   (`' Off '` spegne come `off`); qualunque altro valore lascia il canale acceso.

⚠️ **L'interruttore assente vale acceso**, e così il vuoto. È come lo leggono già il makefile e la
CI, che lo mettono a `off` quando vogliono il canale spento. Per spegnere il canale si scrive `off`:
togliere il parametro non basta.

La funzione legge solo i parametri della sessione: non apre connessioni e non verifica che il
canale risponda. Che risponda lo si scopre al momento di connettersi.

---

### ⭐ Perché restituisce la stringa e non un «sì / no»

Chi chiede se il canale è acceso usa la stringa subito dopo, per connettersi. Con due letture
separate — una per l'interruttore, una per la stringa — ogni chiamante tornerebbe a combinarle a
modo suo, che è proprio il difetto da cui la funzione nasce. Così la risposta è una: `NULL` vuol
dire «non si scrive sul canale», una stringa vuol dire «si scrive, e con questa».

---

### ⛔ Chi legge il canale passa da qui

La usano i quattro lettori del canale: `script.fn_ensure_logconn`,
`dbops.fn_get_or_create_session_tx_id`, `script.fn_log_error_only` e
`maintenance.fn_job_run_log_failure`. Nessuno di loro legge più da sé i tre parametri: un
presidio sul testo lo controlla (vedi *Test*).

Che cosa fa ciascuno quando il canale è spento:

| Chi | Con il canale spento o non configurato |
| --- | --- |
| `fn_ensure_logconn` | non apre niente |
| `fn_get_or_create_session_tx_id` | restituisce la sentinella `script.uuid_nil()` con un `WARNING` e non pubblica il `tx_id` |
| `fn_log_error_only` | un `WARNING`, e l'errore non si registra |
| `fn_job_run_log_failure` | un `WARNING`, e il verbale del job fallito non si scrive |

⚠️ Con `off` — come durante le migrazioni, col makefile e in CI — le scritture sulle tabelle
tracciate prendono quindi la sentinella come `tx_id`, e i due registri fuori transazione non
scrivono. È l'effetto voluto: spento vuol dire spento per tutti.

⚠️ **L'eccezione, per ora: `dbops.fn_audit_log_once`.** L'audit non passa da qui e legge ancora
l'interruttore a modo suo: per lui il parametro assente vale **spento**, e solo il valore esatto `on`
accende il ramo fuori transazione. Resta così finché non si decide che cosa fare di quel ramo: il
dettaglio è nella sua scheda.

---

### Test

* `db/pgtap/script/test-canale-log-v1.sql` — test 1-6: la regola (interruttore assente, `off`, `off`
  con maiuscole e spazi, un altro valore, stringa di soli spazi, precedenza di `myapp.logconn`).
  Test 7-12: con un canale irraggiungibile nessuno dei quattro lettori solleva, e una scrittura su
  una tabella tracciata riesce con la sentinella. Test 13-15: con `off` e un canale che funziona il
  `tx_id` è la sentinella e i due registri non scrivono (si saltano dove il canale non c'è). Test 16,
  il presidio sul testo: nessuna funzione legge da sé i parametri del canale, tranne questa e
  `fn_audit_log_once`.

---

### Note di migrazione

* 2026-11-04 — nasce per D26 di `brief-db-revisione-dbops`: l'interruttore si leggeva in quattro
  modi (assente = acceso in `fn_ensure_logconn`, ma il vuoto = spento; aggirato da
  `fn_get_or_create_session_tx_id`, che bastava la stringa; ignorato da `fn_log_error_only` e
  `fn_job_run_log_failure`), e la stringa in due (la precedenza di `myapp.logconn` la rispettavano
  solo due lettori su quattro).

---

{% include-markdown "signature-core.md" %}
