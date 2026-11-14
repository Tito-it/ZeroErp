## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_codice_maiuscolo`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `CODICE_MAIUSCOLO`: interruttore e template del nome
> * [dbops.automazione_codice_eccezioni](/dbzero/dbops/tabelle/automazione_codice_eccezioni) — le colonne escluse
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove resta ogni azione
>
> Approfondimento funzioni:
>
> * [dbops.fn_codice_maiuscolo_perimetro](/dbzero/dbops/funzioni/fn_codice_maiuscolo_perimetro) — lo stato atteso contro il vivo, e l'azione
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — il trigger che monta
> * [maintenance.proc_automations_lock_columns_job](/dbzero/maintenance/funzioni/proc_automations_lock_columns_job) — il giro notturno che la chiama
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — che cosa è un guasto dell'ambiente
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.8, l'automazione CODICE_MAIUSCOLO
> * [Linee guida Trigger](/linee-guida-trigger#i-trigger-generati) — le regole dei trigger generati

---

### 🎯 Scopo Principale

Porta i trigger `script.trgfn_codice_maiuscolo` allo stato che `dbops.fn_codice_maiuscolo_perimetro`
dichiara: li **crea** dove sono dovuti e mancano, li **rigenera** dove ce n'è più di uno, li
**toglie** dove non sono più dovuti. Il trigger è `BEFORE INSERT OR UPDATE FOR EACH ROW`.

La chiamano la convergenza di ogni migrate (`90_end`, a ogni rilascio) e il giro notturno
`automations_lock_columns`. Non ha un orchestratore: `dbops.fn_run_automations` è ritirata.

---

### La regola è l'interruttore

Per creare un trigger serve una regola `CODICE_MAIUSCOLO` accesa in `dbops.automation_rules_tbl` che
copra schema e tabella e il modo della corsa: da lì viene il **nome** (template
`trg_{table}_a15_codice_maiuscolo_ins_upd`). Senza regola la tabella non si tocca, l'audit lo
registra (`WARN`, azione `NO_RULE`) e la convergenza del migrate si ferma nominandola. Per togliere
non serve regola.

Il trigger vivo si riconosce sempre dalla funzione, qualunque nome abbia: il template serve solo a
dare il nome a quello che si crea.

---

### Audit ed errori

* **Dry run** (`p_dry_run = true`): nessuna DDL, una riga `DRYRUN` per azione.
* **Giro vero**: una riga `OK` per azione, con tabella, trigger atteso e trigger vivi.
* Una DDL che fallisce esce con `E_CODICE_MAIUSCOLO`. Un guasto dell'**ambiente** (connessione,
  risorse, privilegio, lock) si rilancia col suo SQLSTATE, dopo averlo scritto nel registro errori.

---

### Test

`db/pgtap/dbops/test-codice-maiuscolo-v1.sql`: dry run senza DDL (test 10), un trigger per tabella
del tipo giusto (12), idempotenza (19), TOGLIE (21, 22), regola spenta (23-24).

---

### Note di migrazione

* 2026-11-13 — la regola vale per la tabella che nomina: `target_table` si confronta con `=`,
  non più con `ILIKE`, che faceva del `_` di un nome un jolly (una regola su `event_log` copriva
  anche una `eventXlog`). `*all` ha una forma sola, garantita dal CHECK
  `chk_automation_rules_tbl_target_table_nome_esatto` (`90_end/20261112-66`). Testata ri-ancorata
  con `%TYPE`, firma invariata (`20261112-72`).

---

{% include-markdown "signature-core.md" %}
