## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_override_col`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols)   
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_child_fk_col](/dbzero/dbops/funzioni/fn_get_child_fk_col)   
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)   

---

### 🎯 Scopo Principale

(latest review 10-01-26)
La funzione **`dbops.fn_get_override_col(p_schema, p_table, p_role, p_default)`** permette di ottenere in modo centralizzato il nome di una colonna “override” per un ruolo specifico, qualora sia stato definito nella tabella di configurazione `dbops.automation_overrides_cols`. Se non esiste un override registrato, viene restituito il valore di default passato come parametro.

---

### 🔍 Parametri di input

| Parametro   | Tipo | Obbligatorio | Descrizione                                                     |
| ----------- | ---- | :----------: | --------------------------------------------------------------- |
| `p_schema`  | text |      ✔️       | Nome dello schema contenente la tabella target.                 |
| `p_table`   | text |      ✔️       | Nome della tabella target.                                      |
| `p_role`    | text |      ✔️       | Ruolo/etichetta della colonna (es. `fk`, `pk`, `code`).         |
| `p_default` | text |      ✔️       | Valore predefinito da restituire se non è presente un override. |

---

### 📤 Valore di ritorno

`text` – il nome effettivo della colonna da utilizzare secondo la configurazione di override, oppure il valore `p_default` se nessuna regola è trovata.

---

### ⚙️ Flusso logico

1. Interroga la tabella `automation_overrides_cols` cercando una riga che corrisponda a (`schema_name`, `table_name`, `col_role`).
2. Se presente, ritorna il valore di `col_name` configurato.
3. Se assente, ritorna il valore di `p_default` fornito dal chiamante.

---

### 🧩 Casi d’uso tipici

* **Naming flessibile**: quando alcune tabelle non rispettano le convenzioni standard, è possibile definire eccezioni in `automation_overrides_cols`.
* **Automazioni di DDL**: script o funzioni di sistema possono recuperare il nome corretto della colonna chiave senza hardcoding.
* **Compatibilità retroattiva**: consente di gestire tabelle legacy mantenendo invariato il comportamento delle automazioni.

---

### 🛡️ Permessi e sicurezza

* Richiede accesso in lettura a `dbops.automation_overrides_cols`.
* Non modifica dati: è una funzione **read-only**.

---

### 🚀 Esempi di utilizzo

* **Controllo chiave esterna**: un processo cerca la colonna di riferimento per una FK; se per la tabella `clienti` esiste un override (`id_cliente` invece di `cliente_id`), la funzione restituirà `id_cliente`. In assenza, verrà restituito il `p_default` specificato.
* **Normalizzazione naming**: in uno script di generazione indici, usare `fn_get_override_col(schema, table, 'fk', 'default_fk')` assicura che vengano rispettate eventuali eccezioni definite.

---

### 📌 Considerazioni

* La presenza di override va usata con parsimonia: troppe eccezioni riducono l’efficacia delle regole generali.
* La tabella `automation_overrides_cols` diventa la fonte autorevole per mappare ruoli-colonne speciali.

---

### ✅ Benefici

* **Flessibilità**: consente di gestire casi particolari senza alterare le policy generali.
* **Centralizzazione**: tutte le eccezioni sono in un unico punto di configurazione.
* **Manutenibilità**: riduce il rischio di errori hardcoded nel codice SQL.

---

> 🧠 **In sintesi**: `fn_get_override_col` è una funzione utility fondamentale per rendere **le automazioni adattabili a eccezioni di naming o legacy**, mantenendo comunque la coerenza complessiva del sistema.
