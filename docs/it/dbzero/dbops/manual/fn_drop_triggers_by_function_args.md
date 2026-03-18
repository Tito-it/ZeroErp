## 📘 Documentazione Funzione –  `dbops.fn_drop_triggers_by_function_args`

---

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl)
>
Approfondimento funzioni:
>
[`dbops.fn_trigger_exists_by_function`](/dbzero/dbops/funzioni/fn_trigger_exists_by_function)
> [`dbops.fn_trigger_exists_by_name`](/dbzero/dbops/funzioni/fn_trigger_exists_by_name)
> [`dbops.fn_trigger_exists_cascade_by_args`](/dbzero/dbops/funzioni/fn_trigger_exists_cascade_by_args)

---
### 🎯 Scopo Principale
(latest review 13-01-26)
La funzione **`fn_drop_triggers_by_function_args`** elimina tutti i **trigger associati a una tabella** che invocano una determinata funzione di trigger, filtrando in base a **schema**, **nome funzione** e **lista di argomenti**.

---

### Dettagli

* Riceve come parametri:

  * `p_rel regclass` → tabella su cui sono definiti i trigger.
  * `p_func_schema text` → schema della funzione da cercare.
  * `p_func_name text` → nome della funzione di trigger.
  * `VARIADIC p_args text[]` → lista degli argomenti della funzione.

* Scansiona `pg_trigger` per la tabella `p_rel`.
* **Esclude** i trigger interni (`tgisinternal = true`) e le tabelle partizione (`relispartition = true`), così opera solo sui trigger utente del parent.

* Confronta il corpo della definizione del trigger (`pg_get_triggerdef`) con i parametri forniti.

* Per ogni match trovato, esegue `DROP TRIGGER` sulla tabella target.

* Restituisce il **numero di trigger eliminati**.

---

### Utilizzo tipico

1. Durante un **refactor** di funzioni di trigger: elimina i trigger che richiamano la vecchia versione della funzione.
2. In fase di **provisioning automazioni**: pulisce trigger duplicati o obsoleti prima di ricrearli.
3. In combinazione con `fn_run_automations`: garantisce consistenza tra regole e trigger effettivi.

---

### Collegamento con automazione

La funzione è spesso richiamata come **step preliminare** all’applicazione di nuove regole di automazione (`automation_rules_tbl`). Permette di assicurare che non rimangano trigger incoerenti con le regole correnti.

---

### Esempio pratico

Supponiamo di dover aggiornare un trigger che richiama `script.trgfn_tx_id_managed` con specifici argomenti:

```sql
SELECT dbops.fn_drop_triggers_by_function_args(
  'anagrafiche.soggetti',
  'script',
  'trgfn_tx_id_managed',
  VARIADIC ARRAY['tx_id']
);
```

➡️ La funzione rimuoverà tutti i trigger sulla tabella `anagrafiche.soggetti` che invocano quella funzione con quegli argomenti.

---

> **In sintesi**: `fn_drop_triggers_by_function_args` è un componente fondamentale per mantenere **pulito e coerente** l’insieme dei trigger di automazione, specialmente quando le funzioni sottostanti cambiano nel tempo.
