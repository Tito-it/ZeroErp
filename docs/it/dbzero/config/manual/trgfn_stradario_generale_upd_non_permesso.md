## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_stradario_generale_upd_non_permesso()`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
>
> * [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)   
> * [config.stradario](/dbzero/config/tabelle/stradario)     
>
> Approfondimento funzioni:    
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

La trigger function **`config.trgfn_stradario_generale_upd_non_permesso()`** impedisce modifiche non consentite sulle colonne critiche di **`config.stradario_generale`** (`descrizione`, `descrizione_breve`, `toponomastica_id`) quando esistono vie correlate in **`config.stradario`**, segnalando in modo chiaro quale attributo è stato alterato.

---

### 🎯 Scopo Principale

* **Blocco modifiche non consentite**: evitare update di descrizione, descrizione_breve o toponomastica_id in `config.stradario_generale` se il record è già in uso in `config.stradario`.
* **Identificazione precisa**: indicare tramite JSON il nome della colonna modificata e l’ID del record per diagnosticare efficacemente l’errore.
* **Centralizzazione logica**: mantenere il controllo integrità nel database, riducendo complessità lato applicazione.

---

### 🔍 Parametri e Contesto

* **INPUT**: utilizza il record `OLD` (pre-update) e `NEW` (in aggiornamento).
* **Condizione di attivazione**: `BEFORE UPDATE OF descrizione, descrizione_breve, toponomastica_id` su `config.stradario_generale`.
* **Dipendenze**:

  * Tabella `config.stradario` per la verifica di riferimenti esistenti.
  * Funzione `script.fn_log_and_raise_error` per logging e segnalazione errori.

---

### ⚙️ Logica di Esecuzione

1. **Verifica di utilizzo**

   ```plpgsql
   IF NOT EXISTS (
     SELECT 1 FROM config.stradario WHERE stradario_generale_id = OLD.id
   ) THEN
     RETURN NEW;
   END IF;
   ```

   Se non ci sono vie correlate, l’UPDATE procede liberamente.
2. **Controlli colonna per colonna**
   Per ciascuna colonna sensibile, confronta `OLD` vs `NEW`:

   ```plpgsql
   IF OLD.descrizione IS DISTINCT FROM NEW.descrizione THEN
     PERFORM script.fn_log_and_raise_error(
       'database', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
       jsonb_build_object('column','descrizione','id',OLD.id)
     );
   END IF;
   ```

   Ripete la stessa logica per `descrizione_breve` e `toponomastica_id`, specificando sempre il campo modificato.
3. **Ritorno del record**

   ```plpgsql
   RETURN NEW;
   ```

   Dopo i controlli, se non viene lanciata eccezione, il record aggiornato viene restituito.

---



### 💡 Vantaggi Operativi

* **Integrità referenziale**: impedisce modifiche che comprometterebbero la coerenza dei dati stradario.
* **Diagnosi immediata**: il payload JSON indica esattamente quale colonna è stata alterata e l’ID del record.
* **Centralizzazione**: la logica di blocco è consolidata nel database, riducendo dipendenze esterne.

---

> 🧠 **“`trgfn_stradario_generale_upd_non_permesso` garantisce che le definizioni generali non vengano modificate in modo incongruo, proteggendo la consistenza tra stradario_generale e stradario.”**
