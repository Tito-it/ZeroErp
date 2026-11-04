## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_automazione_overlap`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap) — il registro da cui legge i vincoli da creare
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove scrive ogni salto, ogni prova e ogni vincolo creato
>
> Approfondimento funzioni:
>
> * [maintenance.proc_automations_overlap_job](/dbzero/maintenance/funzioni/proc_automations_overlap_job) — il giro che la chiama, a orario e nella convergenza del rilascio
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la scrittura dell'audit
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione OVERLAP fra le altre

---

### 🎯 Scopo Principale

Crea i vincoli di non sovrapposizione (`EXCLUDE USING gist`) che mancano, leggendoli dalle righe
attive di `dbops.automazione_overlap`. È idempotente: una tabella che ha già il suo vincolo si
salta, e a regime il giro non fa DDL.

La chiama `maintenance.proc_automations_overlap_job`, sia dal job a orario sia nella convergenza
del rilascio, in modo `SCHEDULED`. Con `p_dry_run` vero non crea niente e scrive nell'audit che
cosa creerebbe.

---

### Quali righe legge

Le righe con `active` vero il cui `exec_mode` è `AUTO` o è uguale al modo della chiamata, in
ordine di schema e tabella. Per ognuna decide fra tre esiti: **salta**, **prova** (dry run) o
**crea**. Ogni esito lascia una riga in `dbops.audit_log`, con la tabella e il motivo.

---

### ⭐ I salti sono dichiarati, e non fermano il giro

Una riga che non si può applicare non è un errore: la funzione scrive il motivo nell'audit e
passa alla successiva. Lo stato del salto è `WARN` nel giro vero e `DRYRUN` nella prova. I motivi:

* `TABLE_NOT_FOUND` — la tabella del registro non esiste più (rinominata, ritirata): il registro
  non ha una FK verso il catalogo, e una riga rimasta indietro non lascia senza vincolo le tabelle
  che vengono dopo;
* `NO_KEY_COLUMNS` — né colonne né espressioni di chiave;
* `RANGE_COL_MISSING` / `PERIOD_COLUMNS_MISSING` — la colonna del periodo, o una delle due date,
  non c'è;
* `KEY_COLUMNS_NOT_FOUND` — nessuna chiave si risolve: le colonne indicate non esistono e non ci
  sono espressioni. Una colonna di chiave assente, accanto ad altre presenti, viene invece
  **tolta in silenzio** dalla chiave: il vincolo nasce con una chiave più corta di quella
  registrata, quindi più severo, e l'audit non lo dice;
* `EXCLUDE_EXISTS` / `TEMPORAL_UNIQUE_EXISTS` — la tabella ha già un vincolo sul periodo: un
  `EXCLUDE`, o un `UNIQUE … WITHOUT OVERLAPS`, che fa lo stesso lavoro.

---

### Come nasce il vincolo

* **La chiave**: le colonne di `key_columns` che esistono, quotate, e le espressioni di
  `key_expressions` così come sono scritte, tutte con l'uguaglianza.
* **Il periodo**, con la sovrapposizione: la colonna range nativa (`range_col`), se c'è; altrimenti
  l'intervallo costruito dalle due date, con gli estremi di `range_bounds` e una fine vuota che
  vale «per sempre».
* **Il perimetro**: con `where_predicate` il vincolo è parziale, e vale solo fra le righe che lo
  soddisfano; vuoto, vale per tutte.
* **Il nome**: `constraint_name`, o il template `ex_<tabella>_no_overlap`. Se nello schema c'è già
  una relazione con quel nome, la funzione ripiega sul template con il suffisso `_c`.

⛔ `key_expressions` e `where_predicate` entrano nel DDL così come sono: sono testo di fiducia,
che scrive solo chi migra.

---

### ⚠️ Riconosce un vincolo dal periodo, non dalla forma

Il controllo d'idempotenza guarda se la definizione di un vincolo della tabella **nomina la colonna
del periodo**. Non confronta chiave né predicato: un vincolo già creato con una forma diversa da
quella registrata si salta come presente. Per cambiare la forma si toglie il vincolo vecchio, e il
giro successivo crea quello nuovo; la funzione non fa mai `ALTER` né `DROP`.

---

### ⚠️ Dati che si sovrappongono già: il giro si ferma

Se la tabella contiene già righe che violano il vincolo, la creazione fallisce con l'errore di
PostgreSQL e la funzione non lo intercetta: il giro si ferma lì, e le tabelle che vengono dopo
restano senza vincolo fino a quando i dati non si correggono.

---

### Codici errore

La funzione non solleva codici suoi. Un errore della creazione del vincolo (dati che si
sovrappongono, un'espressione o un predicato scritti male) esce con lo SQLSTATE di PostgreSQL.

---

### Test

* `db/pgtap/dbops/test-fn-apply-automazione-overlap-where-predicate-v1.sql` — con un predicato il
  vincolo è parziale: blocca due righe attive sovrapposte e ammette una riga fuori dal predicato;
  senza predicato il vincolo è totale.
* `db/pgtap/dbops/test-fn-apply-automazione-overlap-key-expressions-v1.sql` — un'espressione di
  chiave entra nel vincolo: due righe con la colonna facoltativa vuota si escludono, una vuota e
  una valorizzata no.
* `db/pgtap/dbops/test-overlap-tabella-sparita-v1.sql` — una riga su una tabella inesistente non
  ferma il giro, ed è un salto `TABLE_NOT_FOUND` nell'audit.
* `db/pgtap/pratiche/test-sospensioni-anti-overlap-data-futura.sql` — il vincolo delle sospensioni,
  tolto, torna con l'apply.
* `db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql` — ogni vincolo registrato esiste come
  `EXCLUDE` vero.

---

### Note di migrazione

* 2026-04-12 — la colonna range nativa (`range_col`) accanto alla coppia di date.
* 2026-05-14 — il salto davanti a un `UNIQUE … WITHOUT OVERLAPS`, e i controlli d'esistenza in una
  sola lettura dei vincoli.
* 2026-06-02 — vincoli parziali (`where_predicate`) ed espressioni di chiave (`key_expressions`).
* 2026-11-03 — una riga su una tabella che non esiste è un salto `TABLE_NOT_FOUND`. Prima la
  conversione del nome fermava l'intero giro (`brief-db-revisione-maintenance` D6).

---

{% include-markdown "signature-core.md" %}
