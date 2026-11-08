## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_by_function`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole dei runner che la usano
>
> Approfondimento funzioni:
>
> * [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name) — il controllo per nome, che questi runner non usano più per decidere
> * [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args) — il controllo per funzione **e** argomenti della regola ATTIVO
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id) — uno dei runner che la usano
> * [dbops.fn_run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update) — un altro
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — un altro
> * [dbops.fn_run_automations_date_validita](/dbzero/dbops/funzioni/fn_run_automations_date_validita) — un altro
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — come i runner riconoscono i trigger generati

---

### 🎯 Scopo Principale

Dice se su una tabella esiste almeno un trigger utente che esegue una certa funzione, indicata
con schema e nome. È il controllo di esistenza «per funzione» dei runner delle automazioni:
riconosce un trigger generato anche quando il suo nome non è quello del template.

La usano i runner di audit, `tx_id`, storico e regola del periodo, e decide da sola: se risponde
vero il runner non crea niente, qualunque nome abbia il trigger trovato. Il nome del template serve
solo a creare un trigger nuovo.

---

### Riconosce la funzione, non il trigger

* La funzione si identifica dal **legame** del trigger (`tgfoid`), non dal testo della sua
  definizione: la risposta non dipende dal `search_path` di chi chiama.
* Schema e nome bastano, la firma no. Una funzione trigger non ha argomenti propri, quindi due
  funzioni con lo stesso nome nello stesso schema non possono esistere.
* Non guarda gli **argomenti** del trigger: un trigger sulla stessa funzione con argomenti
  diversi risponde vero. Per le regole in cui gli argomenti fanno la differenza (ATTIVO, una
  coppia di trigger per ogni FK) ci sono i controlli per argomenti, come
  `dbops.fn_trigger_exists_block_by_args`.
* Solo i trigger utente: i trigger interni di PostgreSQL non contano. Non guarda se il trigger è
  abilitato.

⚠️ Risponde vero anche quando i trigger sulla funzione sono **più** di uno: non dice se ce n'è
uno di troppo. Il caso di un trigger scritto a mano che fa lo stesso lavoro di uno generato è
quello che le [linee guida dei trigger](/linee-guida-trigger#i-trigger-generati) vietano.

---

### Una funzione `sql` senza stato

È una lettura dei cataloghi `pg_trigger`, `pg_proc` e `pg_namespace`, senza effetti. Non è
dichiarata `STABLE`, quindi per PostgreSQL è volatile: la risposta si ricalcola a ogni chiamata.

---

### Test

* `db/pgtap/dbops/test-storico-nome-funzione-ritirato-v1.sql` — una madre con il trigger di
  storico montato a mano con un altro nome non ne riceve un secondo; senza trigger, il runner lo
  monta.
* `db/pgtap/dbops/test-storico-salto-trigger-presente-v1.sql` — il ramo in cui il controllo per
  funzione dice «assente» e il nome del template è già preso da un'altra funzione.

---

### Note di migrazione

* 2025-08-21 — nasce con la gemella `fn_trigger_exists_by_name`, nel primo albero dei
  changeSet (`db/changelog/migrations/50_dbops`).
* 2026-11-08 — diventa il solo controllo di esistenza dei runner di `tx_id`, audit, storico e regola
  del periodo: la strategia d'esistenza della regola esce (`20261109-68` … `-71`,
  brief-db-revisione-dbops D17).

---

{% include-markdown "signature-core.md" %}
