## 📚 Documentazione concettuale - Tabella `config.parameters_audit`

> 👀 **Vedi anche**  
>
> Approfondimento Tabelle:   
> - [config.parameter](/dbzero/config/tabelle/parameter)      
>
> Approfondimento funzioni :    
> - [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic)    

La tabella **`config.parameters_audit`** mantiene la **storia** di tutte le modifiche (`UPDATE` e `DELETE`) effettuate sui parametri di sistema definiti in `config.parameters`. Ogni record di audit registra il valore precedente (`old_value`), il valore nuovo (`new_value`), l’azione eseguita e il contesto utente/data.

---

### 🔒 Vincoli

* **PRIMARY KEY**: `parameters_audit_pkey` sulla colonna `id` (IDENTITY).
* **FOREIGN KEY**: `fk_parameters_audit_parameter_code` vincola `parameter_code` al campo `code` di `config.parameters`, garantendo coerenza referenziale.

---

### 🚨 Protezione Dati di Audit

* **Trigger**: `trg_prevent_mod_parameters_audit` (BEFORE UPDATE OR DELETE) su `config.parameters_audit`.
  Esegue la funzione `script.trgfn_prevent_modification_generic()`, che impedisce qualsiasi modifica o cancellazione dei record di audit, assicurando l’inalterabilità della cronologia.

---

### ⚙️ Meccanismo di Audit

1. **Scatto Audit**: utilizza la function `config.trgfn_parameters_audit()` definita su `config.parameters` per:

   * Inserire un record in `config.parameters_audit` ogni volta che su `config.parameters` viene eseguito un **UPDATE** o un **DELETE**.
2. **Campi registrati**:

   * `parameter_code`: codice del parametro modificato.
   * `action`: tipo di operazione (`UPDATE` o `DELETE`).
   * `old_value` / `new_value`: valori prima e dopo la modifica.
   * `reason`: motivo opzionale di modifica (può essere valorizzato da applicazione o trigger wrapper).
   * `user_insert` / `data_insert`: utente e timestamp di creazione del record di audit.

---

### 💡 Vantaggi Operativi

* **Inalterabilità**: la cronologia rimane immutata grazie al trigger di prevenzione.
* **Tracciabilità completa**: ogni modifica a un parametro di sistema viene custodita con valori, utente e timestamp.
* **Supporto al debug**: risalire rapidamente alle configurazioni precedenti e alle ragioni di cambiamento.

---

> 🧠 **“Audit immutabile dei parametri di sistema: garantisce trasparenza e rigore nella gestione delle configurazioni applicative.”**
