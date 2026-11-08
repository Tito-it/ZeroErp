## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_automazione_overlap`

> **Ultimo aggiornamento**: 8 novembre 2026
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
> * [dbops.fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato) — il nome del vincolo
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione OVERLAP fra le altre

---

### 🎯 Scopo Principale

Crea i vincoli di non sovrapposizione (`EXCLUDE USING gist`) che mancano, leggendoli dalle righe
attive di `dbops.automazione_overlap`. È idempotente: una regola che ha già il suo vincolo si
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
* `KEY_COLUMN_MISSING` — una colonna di `key_columns` non esiste sulla tabella: l'audit nomina
  le colonne mancanti. ⭐ La regola si ferma: senza quella colonna il vincolo nascerebbe con una
  chiave più corta di quella registrata, quindi più severo;
* `KEY_COLUMNS_NOT_FOUND` — nessuna chiave si risolve: le colonne indicate non esistono e non ci
  sono espressioni;
* `EXCLUDE_EXISTS` / `TEMPORAL_UNIQUE_EXISTS` — la regola ha già il suo vincolo: l'`EXCLUDE` col
  nome della riga, o un `UNIQUE … WITHOUT OVERLAPS` sul periodo, che fa lo stesso lavoro.

Due salti nascono solo nel giro vero, quando la creazione del vincolo viene rifiutata; sono
sempre `WARN`, e portano lo SQLSTATE:

* `DATI_SOVRAPPOSTI` — la tabella ha già righe che si sovrappongono (`23P01`): il vincolo non
  nasce, e l'audit porta nel dettaglio la prima coppia in conflitto, come la descrive PostgreSQL;
* `NOME_OCCUPATO` — il nome del vincolo è già preso da un altro oggetto dello schema.

---

### Come nasce il vincolo

* **La chiave**: le colonne di `key_columns`, quotate, e le espressioni di `key_expressions` così
  come sono scritte, tutte con l'uguaglianza.
* **Il periodo**, con la sovrapposizione: la colonna range nativa (`range_col`), se c'è; altrimenti
  l'intervallo costruito dalle due date, con gli estremi di `range_bounds` e una fine vuota che
  vale «per sempre».
* **Il perimetro**: con `where_predicate` il vincolo è parziale, e vale solo fra le righe che lo
  soddisfano; vuoto, vale per tutte.
* **Il nome**: `constraint_name`, o il template `ex_<tabella>_no_overlap`, risolti da
  [fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato). Non c'è un
  nome di ripiego: un nome già preso è un salto `NOME_OCCUPATO`.

⛔ `key_expressions` e `where_predicate` entrano nel DDL così come sono: sono testo di fiducia,
che scrive solo chi migra.

---

### ⭐ La regola è applicata solo col suo vincolo

Il controllo d'idempotenza cerca, sulla tabella, l'`EXCLUDE` **col nome della riga**, oppure un
`UNIQUE … WITHOUT OVERLAPS` sul periodo, la forma temporale nativa. Un altro `EXCLUDE` della
tabella, anche se nomina la colonna del periodo, non conta: può avere un'altra chiave, e la
regola riceve comunque il suo vincolo.

⚠️ Il controllo non confronta chiave né predicato: un vincolo col nome giusto e una forma diversa
da quella registrata si salta come presente. Per cambiare la forma si toglie il vincolo vecchio, e
il giro successivo crea quello nuovo; la funzione non fa mai `ALTER` né `DROP`.

⚠️ Per la stessa ragione, **spegnere una regola non toglie il suo vincolo**: togliere un vincolo
d'integrità è una decisione, e la prende chi spegne la riga, con un DROP CONSTRAINT esplicito, e il presidio del vincolo la ricorda finché non è presa.

---

### ⭐ Dati che si sovrappongono già: la regola si ferma, il giro no

Se la tabella contiene già righe che violano il vincolo, la creazione fallisce, la funzione la
intercetta e scrive il salto `DATI_SOVRAPPOSTI`: la tabella resta senza vincolo finché i dati non
si correggono, e le regole che vengono dopo ricevono il loro. Il giro, e con lui la convergenza
del rilascio, va avanti. Lo stesso per un nome già preso (`NOME_OCCUPATO`).

---

### Codici errore

La funzione non solleva codici suoi. Dati sovrapposti e nomi occupati sono salti dichiarati; un
altro errore della creazione del vincolo (un'espressione o un predicato scritti male) esce con lo
SQLSTATE di PostgreSQL e ferma il giro.

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
* `db/pgtap/dbops/test-overlap-regola-e-vincolo-v1.sql` — ogni regola attiva ha il suo vincolo e
  nessuna regola spenta lo ha ancora; un giro con righe già sovrapposte non si ferma, lascia
  `DATI_SOVRAPPOSTI` col dettaglio della coppia e la regola di un'altra tabella riceve il suo
  vincolo; una colonna di chiave assente lascia `KEY_COLUMN_MISSING` e nessun vincolo con la
  chiave più corta; un `EXCLUDE` estraneo sul periodo non impedisce il vincolo della regola; un
  secondo giro non cambia niente.

---

### Note di migrazione

* 2026-04-12 — la colonna range nativa (`range_col`) accanto alla coppia di date.
* 2026-05-14 — il salto davanti a un `UNIQUE … WITHOUT OVERLAPS`, e i controlli d'esistenza in una
  sola lettura dei vincoli.
* 2026-06-02 — vincoli parziali (`where_predicate`) ed espressioni di chiave (`key_expressions`).
* 2026-11-03 — una riga su una tabella che non esiste è un salto `TABLE_NOT_FOUND`. Prima la
  conversione del nome fermava l'intero giro (`brief-db-revisione-maintenance` D6).
* 2026-11-08 — la regola è applicata solo col suo vincolo, per nome (prima bastava un qualsiasi
  `EXCLUDE` che nominasse la colonna del periodo); una colonna di chiave assente è un salto
  `KEY_COLUMN_MISSING` (prima veniva tolta dalla chiave in silenzio); righe già sovrapposte e nome
  occupato sono salti `DATI_SOVRAPPOSTI` e `NOME_OCCUPATO` (prima i dati sovrapposti fermavano il
  giro e la catena di `ci_apply`); il nome viene da `fn_nome_oggetto_dichiarato`, ed esce il
  ripiego col suffisso `_c` (`20261110-06`, `brief-db-revisione-dbops`, giro 10c).

---

{% include-markdown "signature-core.md" %}
