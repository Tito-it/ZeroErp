## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_billing_account_protect_account_code`

> 👀 **Vedi anche**
>
> Approdondmenti tabelle:  
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)   
>
> Approdondmenti funzioni: 
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

---

### 🎯 Scopo Principale

Il trigger `anagrafiche.trgfn_billing_account_protect_account_code`, invocato **prima di ogni UPDATE** su `anagrafiche.billing_account`, impedisce modifiche improprie al campo **`codice (account)`** una volta assegnato.

---

### 🔄 Contesto di Esecuzione

* **Evento**: `BEFORE UPDATE` su `anagrafiche.billing_account`
* **Condizione**: scatta solo se `OLD.codice IS NOT NULL` e `NEW.codice IS DISTINCT FROM OLD.codice`
* **Reazione**: solleva eccezione tramite `script.fn_log_and_raise_error`, bloccando l’update

---


### 🔍 Logica Operativa

1. **Trigger Condition**: verifica che l’operazione sia un `UPDATE`.
2. **Protezione del codice**: controlla che:

   * il vecchio `codice` non sia `NULL`,
   * il nuovo `codice` sia diverso dal vecchio.
3. **Errore**: in caso di modifica non consentita, invoca `script.fn_log_and_raise_error` con codice `E_COLONNA_NON_MODIFICABILE`, indicando la colonna e l’id del record.
4. **Blocco**: il `RAISE EXCEPTION` interno impedisce il completamento dell’UPDATE.

---

### ⚙️ Trigger Collegato

```sql
DROP TRIGGER IF EXISTS trgfn_billing_account_protect_account_code_upd
  ON anagrafiche.billing_account;

CREATE TRIGGER trgfn_billing_account_protect_account_code_upd
  BEFORE UPDATE ON anagrafiche.billing_account
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_billing_account_protect_account_code();
```

---

### 💡 Vantaggi Operativi

* **Integrità**: evita modifiche accidentali o non autorizzate del codice cliente.
* **Centralizzazione degli errori**: utilizza il meccanismo di logging e messaggistica standard (`fn_log_and_raise_error`).
* **Coerenza delle regole**: la logica di protezione è eseguita a livello database, indipendente dal client.

---

### 📌 Best Practice

* Non applicare logica di business aggiuntiva nel trigger; mantenerlo focalizzato sulla protezione di `codice (account)`.
* Aggiornare il codice di errore e il messaggio in `config.messaggi_errore` (`E_COLONNA_NON_MODIFICABILE`) se necessario.
* Testare sempre il comportamento di UPDATE sul campo per garantire compatibilità con eventuali operazioni di migrazione.

---

{% include-markdown "signature-core.md" %}
