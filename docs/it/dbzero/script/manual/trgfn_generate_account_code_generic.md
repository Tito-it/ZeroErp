📘 Documentazione Concettuale – Trigger Function `script.trgfn_generate_account_code_generic()`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:   
>  - [config.account_code](/dbzero/config/tabelle/account_code)   
>  - [dbops.error_log](/dbzero/dbops/tabelle/error_log)   
>
> Approfondimenti funzioni:   
>  - [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)   

---

### 🎯 Scopo Principale

Fornire una **trigger‑function generica** che popola automaticamente la colonna `account_code` quando non è valorizzata, delegando la logica di generazione a `script.fn_generate_codice` in base al tipo di codice specificato (parametro o nome tabella).

---

### 🔍 Meccanismo di Funzionamento

1. **Determinazione del tipo di codice**

   ```plpgsql
   v_code_type := COALESCE(NULLIF(TG_ARGV[0], ''), TG_TABLE_NAME);
   ```

   * Se il primo argomento (`TG_ARGV[0]`) è fornito e non vuoto, lo usa come `type`.
   * Altrimenti, usa il nome della tabella (`TG_TABLE_NAME`).

2. **Verifica e generazione**

   ```plpgsql
   IF NEW.account_code IS NULL OR trim(NEW.account_code) = '' THEN
     NEW.account_code := script.fn_generate_codice(v_code_type);
   END IF;
   ```

   * Controlla se `account_code` è `NULL` o stringa vuota.
   * In caso affermativo, richiama `script.fn_generate_codice` passando il `v_code_type` per ottenere il nuovo codice.

3. **Ritorno**
   Restituisce il record `NEW`, con `account_code` popolato se necessario.

---

### 💡 Vantaggi Operativi

* **Riutilizzabilità**: la stessa funzione trigger serve per più tabelle, basta passare il codice tipo come argomento.
* **Coerenza**: ogni `account_code` viene generato secondo regole centralizzate in `fn_generate_codice`, assicurando formati uniformi.
* **Semplicità**: riduce boilerplate nelle definizioni trigger specifici; nessuna logica duplicata su ogni tabella.
* **Flessibilità**: è possibile personalizzare il `type` passando un parametro nel trigger DDL oppure lasciare che la funzione utilizzi il nome tabella di default.

---

> 🧠 **“Una trigger‑function parametrica come questa semplifica la generazione automatica di codici, migliora la manutenibilità e garantisce format uniformi in tutta la base dati.”**
