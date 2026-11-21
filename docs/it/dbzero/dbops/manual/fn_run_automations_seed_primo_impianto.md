## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_seed_primo_impianto`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) — lo stato che porta sui trigger
> * [dbops.seed_righe](/dbzero/dbops/tabelle/seed_righe) — il registro che riempie all'iscrizione
>
> Approfondimento funzioni:
>
> * [dbops.fn_seed_primo_impianto_divergenze](/dbzero/dbops/funzioni/fn_seed_primo_impianto_divergenze) — il confronto da cui parte
> * [dbops.fn_ruolo_del_migratore](/dbzero/dbops/funzioni/fn_ruolo_del_migratore) — riconosce le righe di seed già presenti
> * [maintenance.proc_automations_lock_columns_job](/dbzero/maintenance/funzioni/proc_automations_lock_columns_job) — chiamante: la convergenza del rilascio e il giro notturno
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — lo stesso stampo, per i blocchi delle cancellazioni
>
> Guide:
>
> * [Framework di automazione DB — 4.9 SEED_PRIMO_IMPIANTO](/guide/automazione-db#49-seed_primo_impianto-la-riga-modificata-dallinstallazione-non-si-riscrive) — la regola

---

### 🎯 Scopo Principale

Il giro della regola `SEED_PRIMO_IMPIANTO`: porta i trigger su
[trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) delle tabelle
dell'ambito allo stato che dichiara
[automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto). Parte
dalle divergenze di
[fn_seed_primo_impianto_divergenze](/dbzero/dbops/funzioni/fn_seed_primo_impianto_divergenze) e le
corregge una per una.

---

### Che cosa fa per ogni divergenza

* `CREA` — monta il trigger, `BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW` in fase `a00`, e
  **iscrive** le righe di seed già presenti: entrano nel registro quelle con `user_insert` uguale a
  `SEED` o a un ruolo del migratore, con `segnata_da = ISCRIZIONE`. Sulla forma figlia monta il
  trigger e non iscrive: la tabella di composizione non ha `id`, e le sue righe seguono il padre.
* `RIGENERA` — toglie i trigger vivi della funzione e rimonta l'atteso. Non ripassa
  dall'iscrizione: il registro c'è già.
* `TOGLIE` — toglie il trigger della riga spenta. Il registro resta.
* `NON_CLASSIFICATA`, `SENZA_ID`, `PADRE_NON_ISCRITTO` — nessuna DDL: un `WARN` nell'audit, e il trigger di prima resta.
* `SCONOSCIUTO` — un trigger della funzione su una tabella che il registro non nomina ferma il giro
  con `E_SEED_PRIMO_IMPIANTO`: toglierlo cancellerebbe in silenzio una protezione.

⚠️ L'iscrizione si fida di `user_insert` una volta sola, quando la tabella entra. Da lì in poi il
segno lo scrive il trigger, e `user_insert` non conta più. Una tabella iscritta senza la colonna
`user_insert` ferma il giro con `E_SEED_PRIMO_IMPIANTO`.

---

### Parametri

* `p_exec_mode` — il modo d'esecuzione del chiamante, che finisce nell'audit.
* `p_schemas` — l'ambito; `NULL` vuol dire quello di `dbops.fn_resolve_scope`.
* `p_dry_run` vero — nessuna DDL: l'azione che farebbe va nell'audit.

Un guasto dell'ambiente (un permesso, un oggetto sparito) esce col suo SQLSTATE: non si traveste
da `E_SEED_PRIMO_IMPIANTO`.

---

### Chi lo chiama

* [proc_automations_lock_columns_job](/dbzero/maintenance/funzioni/proc_automations_lock_columns_job),
  nella convergenza del rilascio e nel giro notturno;
* la rete `runAlways` di `90_end`, a ogni migrate, che si ferma se dopo il giro restano divergenze.

---

### Codici errore

* `E_SEED_PRIMO_IMPIANTO` — trigger sconosciuto, o tabella iscritta senza `user_insert`.

---

### Test

* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql` — la colonna non classificata lascia il
  trigger di prima (21-22); l'iscrizione segna le righe di `SEED` e del migratore e non quelle di uno
  username (23-24); la rigenerazione non ripassa dall'iscrizione (25).
* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql`, asserzioni 1-3 — dopo il giro i
  trigger ci sono, e nessuna divergenza.
* `db/pgtap/ui/test-seed-primo-impianto-ui-software-v1.sql`, asserzione 16 — il runner monta la
  forma figlia e non la iscrive.

---

### Note di migrazione

* 2026-11-17 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive`). Ricalca lo stampo di
  `DELETE_BLOCK`, con un registro suo: la regola non ha una riga in `automation_rules_tbl`.
* 2026-11-20 — la forma figlia e il salto `PADRE_NON_ISCRITTO`.

---

{% include-markdown "signature-core.md" %}
