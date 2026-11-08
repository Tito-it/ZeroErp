## 📘 Documentazione Concettuale – Tabella `dbops.automazione_guard_utility_tipo_ruolo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_guard_utility](/dbzero/dbops/funzioni/fn_run_automations_guard_utility) — il runner che porta i guard allo stato del registro
> * [dbops.fn_guard_utility_divergenze](/dbzero/dbops/funzioni/fn_guard_utility_divergenze) — il confronto fra il guard atteso e quello vivo
> * [dbops.fn_apply_automazione_guard_utility_tipo_ruolo](/dbzero/dbops/funzioni/fn_apply_automazione_guard_utility_tipo_ruolo) — la porta storica, che chiama il runner
> * [dbops.fn_seed_automazione_guard_utility_tipo_ruolo](/dbzero/dbops/funzioni/fn_seed_automazione_guard_utility_tipo_ruolo) — segnala le tabelle che qualificano e non sono a catalogo
> * [script.trgfn_guard_utility_tipo_ruolo_by_cols](/dbzero/script/funzioni/trgfn_guard_utility_tipo_ruolo_by_cols) — la funzione trigger montata, che riceve le due colonne come argomenti
> * [script.fn_guard_utility_tipo_ruolo](/dbzero/script/funzioni/fn_guard_utility_tipo_ruolo) — la regola: il ruolo deve essere di un tipo ammesso per l'utility
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione GUARD utility/tipo ruolo fra le altre

---

### 🎯 Scopo Principale

Il catalogo delle tabelle su cui il framework monta il guard **utility → tipo ruolo**: una riga
dice quale colonna porta l'utility e quale il soggetto-ruolo, e il guard rifiuta una riga il cui
ruolo non è di un tipo ammesso per quell'utility.

---

### ⭐ È un mirror del CSV

Le righe vengono dal CSV `80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv`, ricaricato
a ogni migrate, come le altre tabelle `automazione_*` di `dbops`. Una tabella si aggiunge o si
toglie dal CSV; la funzione di rilevazione dallo schema non scrive più qui, e segnala soltanto le
tabelle che qualificano e mancano.

Le righe non si cancellano: una tabella considerata e lasciata fuori resta nel CSV con `enabled`
falso. La riga spenta dice che la tabella è stata valutata, cosa che l'assenza non direbbe, e
il runner toglie il guard che vi trova. ⛔ Un guard vivo su una tabella senza riga ferma il runner
con `E_GUARD_UTILITY`: per togliere un guard si spegne la riga.

---

### Che cosa dice una riga

* `schema_name`, `table_name` — la tabella, unica nel catalogo;
* `utility_column` — la colonna dell'utility, di norma `utility_id`;
* `soggetto_ruolo_column` — la colonna del soggetto-ruolo da giudicare, con o senza prefisso
  (`emittente_soggetto_ruolo_id`, `soggetto_ruolo_id`): il guard è generico, e la colonna la
  dichiara la riga. Se una delle due colonne non esiste, il runner lo segnala con un
  `WARN COLUMN_MISSING` e non monta niente;
* `enabled` — l'interruttore: accesa, la tabella ha il guard; spenta, il runner lo toglie;
* `exec_mode` — il contesto d'esecuzione (`AUTO` vale per tutti); non può essere vuoto;
* `trigger_name` — il nome del trigger, se non va bene quello del template
  (`trg_<tabella>_a10_guard_utility_tipo_ruolo_ins_upd`); cambiarlo rigenera il guard col nome
  nuovo;
* `meta` — spazio libero, che il runner non legge.

---

### Test

* `db/pgtap/dbops/test-automazione-guard-utility-tipo-ruolo.sql` — la riga di
  `anagrafiche.emittenti_fiscali_utilities` è a catalogo e accesa, con le colonne che la tabella
  ha davvero; ogni riga accesa nomina colonne che esistono; la funzione di rilevazione non scrive
  nel catalogo.
* `db/pgtap/dbops/test-guard-utility-convergenza-v1.sql` — su tutto l'ambito i guard vivi sono
  quelli del registro; il comportamento del runner su ogni azione è nella sua pagina.

---

### Note di migrazione

* 2026-02-16 — nasce il catalogo, scritto dalla funzione di rilevazione con un inserimento che
  non correggeva mai una riga già scritta.
* 2026-08-18 — il catalogo diventa un mirror del CSV, e la rilevazione smette di scrivere. Le
  righe di tabelle che avevano perso `utility_id` o erano state rinominate restano nel CSV,
  spente (`brief-db-automazione-guard-utility-righe-sfuggite`).
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-08 — il registro lo esegue un runner che converge, `fn_run_automations_guard_utility`,
  con il suo processo `automations_guard_utility`: una riga spenta toglie il guard, un
  `trigger_name` cambiato lo rigenera, e la colonna `soggetto_ruolo_id` senza prefisso non viene
  più scartata (`brief-db-revisione-dbops`, giro 10c).

---

{% include-markdown "signature-core.md" %}
