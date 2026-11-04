## 📘 Documentazione Concettuale – Tabella `dbops.automation_cleanup_exclusions`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` e `CLEANUP_PURGE` da cui l'esclusione sottrae una tabella
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito che il giro percorre prima di guardare le esclusioni
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove il salto lascia traccia
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — l'unico lettore della tabella
> * [dbops.fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) — la scadenza alla nascita, che l'esclusione non ferma
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

L'elenco delle tabelle che il giro di cleanup **non tocca**: per una tabella esclusa non si
calcola la scadenza `cleanup_at` e non si cancellano le righe scadute, qualunque regola la copra.

Serve quando una regola generica (per esempio una `CLEANUP_PURGE` su tutte le tabelle di uno
schema) prenderebbe anche una tabella che va conservata. La chiave è la coppia
(`schema_name`, `table_name`): un'esclusione per tabella, con il suo motivo in `reason`.

---

### L'esclusione vale per tabella, non per regola

Il giro di [fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)
percorre le tabelle dell'ambito e, prima di cercare le regole, guarda se la tabella è esclusa con
`enabled` vero. Se lo è, la salta **intera**: né `CLEANUP_AT` né `CLEANUP_PURGE`. Non si può
escludere una tabella da una regola sola.

Il salto lascia in `dbops.audit_log` una riga con status `WARN` e motivo `EXCLUDED` nei
parametri: chi legge l'audit vede che la tabella è stata vista e lasciata stare di proposito.

`enabled` falso tiene la riga come promemoria e restituisce la tabella al giro dalla corsa
successiva. Non c'è un controllo che la tabella esista: un'esclusione su una tabella che non c'è
è inerte.

---

### ⚠️ Che cosa l'esclusione non ferma

* **Le chiamate dirette.** `dbops.fn_apply_cleanup_at` e `dbops.fn_purge_cleanup_expired` non
  leggono questa tabella: chi le chiama a mano su una tabella esclusa la tratta comunque.
* **La scadenza alla nascita.** Su una tabella che ha il trigger
  `dbops.trgfn_cleanup_at_alla_nascita`, la scadenza la sceglie
  [fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) dalle sole regole
  `CLEANUP_AT`, senza guardare le esclusioni. Una tabella esclusa con quel trigger riceve quindi
  `cleanup_at` alle righe nuove, ma il giro non le cancella mai.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — con l'esclusione attiva il giro non cancella la
  riga scaduta; con l'esclusione disattivata la cancella. La prova mette in ambito la propria
  tabella, perché senza ambito le due asserzioni non eserciterebbero il giro.

---

### Note di migrazione

* 2026-02-07 — nasce col framework di cleanup basato su `cleanup_at`.

---

{% include-markdown "signature-core.md" %}
