## 📘 Documentazione Concettuale – Tabella `dbops.automation_overrides_cols`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole che, per una tabella, usano il nome di colonna scritto qui
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col) — la lettura: il nome di qui, o il default del chiamante
> * [dbops.fn_run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update) — legge `AUDIT_TS` e `AUDIT_USER`
> * [dbops.fn_run_automations_storico_provision](/dbzero/dbops/funzioni/fn_run_automations_storico_provision) — legge `STORICO_FK` e `STORICIZZA_COL`
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — legge `STORICO_FK`
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — legge `ATTIVO_COL` del padre e del figlio
> * [dbops.fn_get_lookup_codici](/dbzero/dbops/funzioni/fn_get_lookup_codici) — legge `CODICE_COL` e `CODICE_INTERNO_COL`
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Le eccezioni di **nome di colonna** per tabella: quando una tabella chiama in un altro modo una
colonna che il framework si aspetta con un nome standard, qui si scrive il nome vero. Una riga
dice, per (`schema_name`, `table_name`), che la colonna con il ruolo `col_role` si chiama
`col_name`.

La chiave è (`schema_name`, `table_name`, `col_role`): un solo nome per ruolo e tabella. Il
confronto è esatto: niente modelli, niente `*all`.

---

### Il nome si risolve in tre passi

Chi ha bisogno di una colonna chiede a `dbops.fn_get_override_col` il nome per il suo ruolo,
passando il proprio default. Vince:

1. la riga di questa tabella, se c'è;
2. altrimenti il default del chiamante, che per `AUDIT_TS` e `AUDIT_USER` è il parametro della
   regola `AUDIT_UPDATE` (`audit_ts`, `audit_user`) e, se manca, il nome standard.

La lettura non controlla che la colonna esista: lo fa, dove serve, chi la usa.

---

### I ruoli che qualcuno legge

* `ATTIVO_COL` — la colonna booleana dello stato attivo, sul padre e sul figlio dei guard ATTIVO.
  Default `attivo`.
* `AUDIT_TS`, `AUDIT_USER` — le colonne dell'ultima modifica scritte dal trigger di audit.
  Default `data_update` e `user_update`.
* `STORICO_FK` — la colonna della tabella di storico che punta alla riga di origine. Default
  `<tabella>_id`, che non va bene quando il nome della tabella è al plurale: il seed la dichiara
  per esempio per `anagrafiche.clienti` (`cliente_id`).
* `STORICIZZA_COL` — la colonna che dice se una riga si storicizza. Default `storicizza`.
* `CODICE_COL`, `CODICE_INTERNO_COL` — le colonne che `dbops.fn_get_lookup_codici` espone come
  `codice` e `codice_interno`, per una tabella che ha una chiave naturale con un altro nome (per
  esempio `codice_iso` su `config.lingue`). Senza riga, la funzione guarda la struttura della
  tabella, e senza `codice_interno` restituisce un valore vuoto.

⚠️ `col_role` è testo libero, senza vincolo: un ruolo scritto male non solleva niente, e la riga
resta inerte. Un ruolo nuovo serve solo se un automatismo lo legge.

---

### Quando il nome si legge

Non tutti i lettori lo leggono nello stesso momento:

* il runner dell'audit lo legge al giro, per decidere se montare il trigger: senza le due colonne
  la tabella non riceve l'audit;
* la preparazione dello storico lo legge quando crea la tabella di storico: un `STORICO_FK`
  aggiunto dopo non rinomina una colonna già creata;
* i guard ATTIVO leggono `ATTIVO_COL` del figlio a ogni esecuzione, e il runner passa quella del
  padre come argomento del trigger.

Un override si scrive quindi **prima** che la tabella entri nel giro.

---

{% include-markdown "signature-core.md" %}
