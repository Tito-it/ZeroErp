## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_by_name`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola che sceglie la strategia di esistenza (`existence_strategy`)
>
> Approfondimento funzioni:
>
> * [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function) — l'altra metà della strategia, per funzione
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — compone il nome che i runner cercano qui
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id) — uno dei runner che la usano
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — il runner che riconosce i trigger solo per nome
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — le strategie di esistenza delle regole

---

### 🎯 Scopo Principale

Dice se su una tabella esiste un trigger utente con un nome **esatto**. È il controllo di
esistenza «per nome» dei runner delle automazioni: prima di creare un trigger generato, il
runner chiede se il nome del template c'è già.

La usano i runner di audit, `tx_id`, storico, ATTIVO, regola del periodo e blocco delle
cancellazioni. Con la strategia `BY_NAME` decide da sola; con `BOTH` basta che risponda vero lei
o il controllo per funzione perché il runner non crei niente.

---

### Che cosa guarda e che cosa no

* Solo i trigger **utente**: i trigger interni di PostgreSQL (quelli delle FK) non contano. Un
  `CONSTRAINT TRIGGER` scritto con il suo nome è un trigger utente, e conta.
* Il nome si confronta **così com'è**, senza normalizzare maiuscole né spazi.
* Non guarda la funzione né gli argomenti, né se il trigger è abilitato: un trigger con il nome
  giusto e un contenuto qualsiasi risponde vero.

⚠️ **Il nome cercato deve essere quello che PostgreSQL ha salvato.** Un nome oltre 63 caratteri
PostgreSQL lo tronca quando crea il trigger. Se il chiamante cerca il nome intero, la risposta è
sempre falsa, e il runner prova a ricreare un trigger che c'è già. I runner che compongono il
nome con `dbops.fn_name_from_template` sono al riparo, perché lì il nome lungo si tronca e
riceve un hash. Le regole sui nomi stanno nelle
[linee guida dei trigger](/linee-guida-trigger#il-nome-del-trigger).

---

### Una funzione `sql` senza stato

È una lettura del catalogo `pg_trigger`, senza effetti. Non è dichiarata `STABLE`, quindi per
PostgreSQL è volatile: la risposta si ricalcola a ogni chiamata, ed è quello che serve a un
runner che crea trigger mentre controlla.

---

### Test

Nessun pgTAP la chiama per nome. La presidiano in modo indiretto i test dei runner che passano
dalla strategia `BOTH`, per esempio `db/pgtap/dbops/test-storico-nome-funzione-ritirato-v1.sql`
(una madre con il trigger di storico non ne riceve un secondo).

---

### Note di migrazione

* 2025-08-21 — nasce con la gemella `fn_trigger_exists_by_function`, nel primo albero dei
  changeSet (`db/changelog/migrations/50_dbops`).

---

{% include-markdown "signature-core.md" %}
