## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_upd_audit_data_user_generic`


La trigger function **`script.trgfn_upd_audit_data_user_generic()`** si occupa di aggiornare automaticamente i campi di audit `data_update` e `user_update` immediatamente prima di ogni operazione di update sul record, garantendo la tracciabilità delle modifiche.

---

### 🎯 Scopo Principale

* **Audit automatico**
  Assicurare che ogni modifica a una riga di tabella sia registrata con timestamp (`data_update`) e utente (`user_update`) correnti.
* **Centralizzare la logica di update audit**
  Evitare di replicare manualmente la medesima assegnazione in ogni trigger `BEFORE UPDATE` delle varie tabelle.

---

### 🔍 Parametri e Contesto

* **Nessun parametro**: la funzione opera su `NEW`, modificando in-place i campi di audit.
* **Trigger associati**: va utilizzata con `BEFORE UPDATE` su qualsiasi tabella che possieda i campi:

  * `data_update TIMESTAMP WITH TIME ZONE`
  * `user_update TEXT` (o VARCHAR)

Esempio di associazione DDL:

```sql
CREATE TRIGGER trg_upd_<nome_tabella>_audit_data_user
  BEFORE UPDATE ON <nome_schema>.<nome_tabella>
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic();
```

---

### ⚙️ Comportamento

1. **Aggiornamento timestamp**

   ```plpgsql
   NEW.data_update := CURRENT_TIMESTAMP;
   ```
2. **Aggiornamento utente**

   ```plpgsql
   NEW.user_update := CURRENT_USER;
   ```
3. **Restituzione del record**

   ```plpgsql
   RETURN NEW;
   ```

Queste assegnazioni avvengono subito prima che l’UPDATE sia eseguito, sovrascrivendo eventuali valori preesistenti.

---

### 🔒 Valore di Ritorno

* **`trigger`**
  Restituisce il record `NEW` con i campi di audit aggiornati.

---

### 💡 Vantaggi Operativi

* **Uniformità**
  Un’unica trigger function per tutte le tabelle, garantendo comportamento omogeneo.
* **Riduzione di codice duplicato**
  Non serve inserire manualmente assegnazioni di audit in ogni trigger.
* **Sicurezza e tracciabilità**
  Ogni modifica alle tabelle viene automaticamente marcata con data e utente, migliorando la compliance e il debugging.
* **Facilità di estensione**
  Basta aggiungere un trigger `BEFORE UPDATE` replicando lo stesso pattern su nuove tabelle.

---

> 🧠 **“Automatizzare l’audit delle modifiche con una trigger function generica assicura coerenza, riduce il boilerplate e aumenta la tracciabilità.”**
