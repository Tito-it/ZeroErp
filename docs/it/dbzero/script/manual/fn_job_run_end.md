## Documentazione Concettuale – Funzione `script.fn_job_run_end`

> **Vedi anche**
>
**Tabelle correlate:**
>
[maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log)
>
**Funzioni correlate:**
>
[script.fn_job_run_start](/dbzero/script/funzioni/fn_job_run_start),
[maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)

---
### 🎯 Scopo Principale
(latest review 18-06-2026 — registrazione run job headless)

La funzione **`script.fn_job_run_end`** chiude un **run** aperto da
[`script.fn_job_run_start`](/dbzero/script/funzioni/fn_job_run_start): valorizza esito,
tempi, errori e `meta` sulla riga [`maintenance.job_run_log`](/dbzero/maintenance/tabelle/job_run_log)
e rilascia l'advisory lock di sessione.

---

### Parametri di input

| Parametro         | Tipo                                            | Default | Descrizione                                       |
| ----------------- | ----------------------------------------------- | ------- | ------------------------------------------------- |
| `p_id`            | `maintenance.job_run_log.id%TYPE`               | —       | PK del run (da `fn_job_run_start`).               |
| `p_ok`            | `maintenance.job_run_log.ok%TYPE`               | —       | Esito del run.                                    |
| `p_message`       | `maintenance.job_run_log.message%TYPE`          | `NULL`  | Messaggio leggibile.                              |
| `p_rows_affected` | `maintenance.job_run_log.rows_affected%TYPE`    | `NULL`  | Righe processate (informativo).                   |
| `p_error_code`    | `maintenance.job_run_log.error_code%TYPE`       | `NULL`  | Codice errore (su fallimento).                    |
| `p_error_detail`  | `maintenance.job_run_log.error_detail%TYPE`     | `NULL`  | Dettaglio errore.                                 |
| `p_meta`          | `maintenance.job_run_log.meta%TYPE`             | `NULL`  | Riepilogo **generico** del run (JSONB).           |
| `p_lock_key`      | `text`                                          | `NULL`  | Stessa identità logica passata a `fn_job_run_start` (per lo sblocco). |

---

### Output

`void`. Aggiorna la riga `p_id`: `ended_at = clock_timestamp()`, `ok`, e (se non NULL)
`message`/`rows_affected`/`error_code`/`error_detail`/`meta`.

---

### ⛔ Una corsa saltata non si chiude *(rev 2026-10-10)*

* Se la riga `p_id` è **saltata** (`saltata = true`: `fn_job_run_start` ha trovato il lock
  occupato) la funzione **rifiuta** con `E_JOB_RUN_SALTATA_NON_CHIUDIBILE` (classe
  `TECNICO`). La corsa non ha fatto lavoro e nasce già chiusa, senza esito: chiuderla le
  scriverebbe un esito e la farebbe passare per una corsa vera. Lo produce solo un
  chiamante che ha ignorato `acquired = false`.
* Fino al 2026-10-10 questo percorso («`end` dopo `skip`») era tollerato: nessun
  chiamante lo usa più (il backend, su `acquired = false`, non chiama la funzione).

### Robustezza della doppia chiusura

* L'advisory lock viene rilasciato **solo se realmente posseduto da questo flusso**: se la
  riga era già chiusa (una seconda chiusura, o una *skip* scritta prima del 2026-10-10
  con `saltata = false`), l'unlock viene saltato → niente warning `pg_advisory_unlock` su
  lock non posseduto.
* Lo sblocco usa lo **stesso** `classid` + `hashtext(p_lock_key)` di `fn_job_run_start`
  (unlock simmetrico), sulla **stessa** connessione (vincolo lock di sessione).

---

### Regole principali

* **`SECURITY DEFINER`** con `search_path` fisso e tabella fully-qualified (come
  `fn_job_run_start`): i ruoli batch hanno solo `EXECUTE`, nessun DML diretto.
* `EXECUTE` **revocato da PUBLIC**.
* Contratto col BE: su `acquired=false` (skip) il chiamante **non** invoca `fn_job_run_end`
  (la riga è già chiusa). Dal 2026-10-10 non è più solo un contratto: la funzione lo
  rifiuta (sopra).

---

### Esempio d'uso

```sql
-- chiusura happy-path
SELECT script.fn_job_run_end(
  p_id    => 123,
  p_ok    => true,
  p_message => 'done',
  p_meta  => '{"emittenti": 4, "falliti": 0}'::jsonb,
  p_lock_key => 'run_fatturazione_batch:immediata'
);

-- chiusura su errore
SELECT script.fn_job_run_end(123, false, 'boom', NULL, 'P0001', 'stack...', NULL,
                             'run_fatturazione_batch:immediata');
```

---

### ⭐ Rev 2026-10-16 — `p_sqlstate`

Parametro nuovo **in coda**, con default `NULL`: il backend vi passa lo SQLSTATE di un
errore che è passato dal database (disco pieno, connessione caduta), che prima andava
perso dietro il nome dell'eccezione. `p_error_code` resta il codice del backend. Le
chiamate a otto argomenti continuano a funzionare.
*Brief: `brief-db-presidio-job-run-a-chi-tocca.md` §4.2.*

---

{% include-markdown "signature-core.md" %}
