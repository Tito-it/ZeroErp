## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_by_name`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole, con il template del nome
>
> Approfondimento funzioni:
>
> * [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function) — il controllo con cui i runner riconoscono i trigger generati
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — compone il nome che i runner cercano qui
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — la usa per sapere se il trigger riconosciuto ha già il nome atteso
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — il runner che riconosce i trigger solo per nome
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — come i runner riconoscono i trigger generati

---

### 🎯 Scopo Principale

Dice se su una tabella esiste un trigger utente con un nome **esatto**. È il controllo di
esistenza «per nome» dei runner delle automazioni: prima di creare un trigger generato, il
runner chiede se il nome del template c'è già.

I runner di audit, `tx_id`, storico e regola del periodo non la usano: riconoscono il trigger dalla
funzione. La usano il runner ATTIVO, che riconosce il trigger dagli argomenti e chiede qui solo se
quello trovato ha già il nome atteso (se no lo rigenera), e il runner del blocco delle
cancellazioni, che riconosce i trigger solo per nome.

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

Nessun pgTAP la chiama per nome. La presidia in modo indiretto
`db/pgtap/dbops/test-attivo-due-fk-stessa-coppia-v1.sql`: un trigger ATTIVO col nome di prima si
rigenera col nome atteso, e un secondo giro non ricrea niente.

---

### Note di migrazione

* 2025-08-21 — nasce con la gemella `fn_trigger_exists_by_function`, nel primo albero dei
  changeSet (`db/changelog/migrations/50_dbops`).
* 2026-11-08 — i runner di `tx_id`, audit, storico e regola del periodo non la usano più per
  decidere; ATTIVO la usa solo per il nome atteso: la strategia d'esistenza della regola esce
  (`20261109-68` … `-72`, brief-db-revisione-dbops D17).

---

{% include-markdown "signature-core.md" %}
