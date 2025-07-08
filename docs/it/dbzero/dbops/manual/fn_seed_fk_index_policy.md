## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_fk_index_policy()`

> 👀 **Vedi anche** 
>
> Approfondimento Tabelle:   
> - [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)      
>
> Approfondimento funzioni:   
> - [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/manual/vw_fk_con_indice_missing_policy)  


La funzione **`dbops.fn_seed_fk_index_policy()`** popola automaticamente la tabella `dbops.fk_index_policy` con le foreign key **già indicizzate** ma **non ancora presenti** in policy, marcandole come `consentito = true` e `generated_by_script = true`.

---

### 🎯 Scopo Principale

* **Sincronizzazione iniziale**
  Aggiunge in `fk_index_policy` tutte le FK con indice esistente rilevate in `vw_fk_con_indice_missing_policy`.
* **Automazione**
  Evita inserimenti manuali per policy già coperte da indice.
* **Flag di origine**
  Imposta `generated_by_script = true` per distinguere le righe create automaticamente.

---

### 🔍 Parametri di Input

Questa funzione **non** richiede parametri: agisce su tutti i record presenti nella view `dbops.vw_fk_con_indice_missing_policy`.

---

### ⚙️ Flusso Logico

1. **Selezione FK da view**
   Recupera `schema_name`, `table_name`, `constraint_name` e `create_index_suggestion` dalla view.
2. **Inserimento con ON CONFLICT**
   Usa `INSERT ... ON CONFLICT (schema_name, table_name, constraint_name) DO NOTHING` per:

   * `consentito = true`
   * `generated_by_script = true`
   * mantenere qualsiasi `note` o valore preesistente se già presente.

---


---

### 🚀 Utilizzo

```sql
-- Esegui il popolamento iniziale:
SELECT dbops.fn_seed_fk_index_policy();
```

Può essere integrata in un changeSet Liquibase con `runAlways: false` (solo esecuzione iniziale) per assicurare che tutte le FK con indice siano registrate in policy.

---

### 💡 Vantaggi Operativi

* **Completezza**: nessuna FK indicizzata resta scoperta da policy.
* **Tracciabilità**: `generated_by_script` segnala le policy create automaticamente.
* **Semplicità**: un’unica chiamata per inizializzare la policy.
* **Integrazione CI/CD**: può essere collocata in uno step di migrazione finale senza duplicare record.

---

> 🧠 **“Con `fn_seed_fk_index_policy()` automatizziamo la scoperta e l’inclusione delle FK già indicizzate, mantenendo la policy sempre completa e allineata.”**