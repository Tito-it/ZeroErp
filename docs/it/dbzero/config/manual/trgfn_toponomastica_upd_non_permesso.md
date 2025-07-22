## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_toponomastica_upd_non_permesso()`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:   
> - [config.toponomastica](/dbzero/config/tabelle/toponomastica)    
> - [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)    
>
> Approfondimento funzioni:   
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

La trigger function **`config.trgfn_toponomastica_upd_non_permesso()`** impedisce modifiche non consentite sul catalogo delle toponomastiche, bloccando l’**UPDATE** di `descrizione` quando la voce è già in uso in **`config.stradario_generale`**.

---

### 🎯 Scopo Principale

* **Protezione semantica**: garantire coerenza tra topografia e stradario evitando rinominazioni dirette di toponomastiche già in uso.
* **Decisione di design**: anziché storicizzare o consentire modifiche parziali, obbligare alla creazione di nuove topografìe per cambiare descrizione.
* **Centralizzazione**: concentrare la logica di blocco in una sola funzione trigger per ridurre complessità applicativa.

---

### 🔍 Parametri e Contesto

* **Ambito**: `BEFORE UPDATE OF descrizione` sulla tabella **`config.toponomastica`**.
* **Condition**: attivazione solo se il record è referenziato in `config.stradario_generale` tramite il campo `toponomastica_id`.
* **Dipendenze**:

  * Tabella `config.stradario_generale` per la verifica dei riferimenti.
  * Funzione `script.fn_log_and_raise_error` per generare errori strutturati.

---

### ⚙️ Flusso di Esecuzione Dettagliato

1. **Verifica utilizzo**

   ```plpgsql
   IF NOT EXISTS (
     SELECT 1
       FROM config.stradario_generale
      WHERE toponomastica_id = OLD.id
   ) THEN
     RETURN NEW;
   END IF;
   ```

   Se la toponomastica non è usata, l’UPDATE di `descrizione` procede normalmente.

2. **Blocco modifica**

   ```plpgsql
   IF OLD.descrizione IS DISTINCT FROM NEW.descrizione THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       TG_NAME,
       'E_COLONNA_NON_MODIFICABILE',
       jsonb_build_object('column','descrizione','id',OLD.id)
     );
   END IF;
   ```

   Se la `descrizione` viene cambiata, la funzione lancia un errore bloccando l’operazione e indicando quale colonna e ID sono coinvolti.

3. **Ritorno**

   ```plpgsql
   RETURN NEW;
   ```

   In ogni caso, il record viene restituito (se l’errore non è stato sollevato), anche se normalmente l’operazione si interrompe al lancio dell’eccezione.

---

### 🔒 Motivazione e Benefici

* **Integrità referenziale logica**: impedendo modifiche di descrizioni in uso, si evita la discrepanza tra entità generali e record associati.
* **Chiarezza operativa**: chiara segnalazione dell’errore con payload JSON specifico, facilita debug e supporto.
* **Strategia di manutenzione**: per modificare la descrizione di una toponomastica esistente, è necessario creare un nuovo record, preservando la storia e evitando side effect.
* **Leggerezza**: rispetto alla storicizzazione completa, questo approccio è più semplice e leggero quando la modifica non è prevista come operazione comune.

---

> 🧠 **“Con `trgfn_toponomastica_upd_non_permesso`, Zero ERP tutela la coerenza dello stradario imponendo la creazione di nuove toponomastiche per ogni cambiamento, piuttosto che modifiche in-place.”**
