## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_istanze_utilities_protect_codice`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle: 
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>
> Approfondimenti funzioni: 
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale

(latest review 28-12-25)
Il trigger `anagrafiche.trgfn_istanze_utilities_protect_codice`, eseguito **prima di ogni UPDATE** su `anagrafiche.istanze_utilities`, impedisce modifiche non autorizzate al campo **`codice (istanza)`** una volta impostato.

---

### 🔄 Contesto di Esecuzione

* **Evento**: `BEFORE UPDATE` sulla tabella `anagrafiche.istanze_utilities`.
* **Condizione**: scatta quando:

  * l’operazione è `UPDATE`;
  * `OLD.codice` **non** è `NULL`;
  * `NEW.codice` è diverso da `OLD.codice`.
* **Effetto**: blocca l’UPDATE e solleva eccezione tramite il logging centralizzato.

---


### 🔍 Logica Operativa

1. **Verifica UPDATE**: controlla che l’operazione sia un `UPDATE`.
2. **Protezione del codice**:

   * `OLD.codice IS NOT NULL` garantisce che non blocchi la generazione iniziale.
   * `NEW.codice IS DISTINCT FROM OLD.codice` individua tentativi di modifica.
3. **Errore centralizzato**: invoca `script.fn_log_and_raise_error` con codice `E_COLONNA_NON_MODIFICABILE`, includendo:

   * l’`id` del record,
   * il nome della colonna protetta.
4. **Blocco DML**: il `RAISE EXCEPTION` generato dalla funzione di logging annulla l’`UPDATE`.

---

### ⚙️ Trigger Collegato

```sql
DROP TRIGGER IF EXISTS trg_istanze_utilities_protect_codice
  ON anagrafiche.istanze_utilities;

CREATE TRIGGER trg_istanze_utilities_protect_codice
  BEFORE UPDATE ON anagrafiche.istanze_utilities
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_protect_codice_upd();
```

---

### 💡 Vantaggi Operativi

* **Integrità dei codici**: assicura che ogni `codice (istanza)` rimanga immutato dopo la prima assegnazione.
* **Logging unificato**: errore registrato e sollevato tramite `fn_log_and_raise_error`.
* **Sicurezza**: impedisce modifiche accidentali o malevole direttamente a livello database.

---

### 📌 Best Practice

* Tenere il trigger focalizzato sulla protezione del codice: separare altri controlli in trigger diversi.
* Assicurarsi che `config.messaggi_errore` contenga il codice `E_COLONNA_NON_MODIFICABILE` con testo adeguato.
* Testare scenari di UPDATE con e senza modifica del codice per verificare il comportamento.

---

{% include-markdown "signature-core.md" %}
