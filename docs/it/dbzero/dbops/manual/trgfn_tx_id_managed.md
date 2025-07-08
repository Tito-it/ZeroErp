## 📘 Documentazione Concettuale – Trigger Function `dbops.trgfn_tx_id_managed()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids)      
>
> Approfondimento funzioni :    
> - [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id)    
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)    

La trigger function **`dbops.trgfn_tx_id_managed()`** viene eseguita **`BEFORE INSERT OR UPDATE`** su ogni tabella che contiene la colonna `tx_id` e centralizza la **logica di validazione**, **generazione** e **assegnazione** dell’**UUID di transazione** per la riga in corso di inserimento/aggiornamento.

---

### 🎯 Obiettivi e Ruolo

1. **Bypass configurabile**: permette di saltare la generazione e verifica del `tx_id` in contesti speciali (es. test, migrazioni, debug).
2. **Validazione integrità**: garantisce che un `tx_id` presente in sessione esista già in `dbops.transaction_ids`, altrimenti segnala un warning e resetta a `nil`.
3. **Generazione on-demand**: se non è presente alcun `tx_id` in sessione e il bypass è disabilitato, invoca `dbops.fn_get_or_create_session_tx_id()` per creare un nuovo identificativo.
4. **Assegnazione uniforme**: popola la colonna `NEW.tx_id` con il valore deciso dal flusso, assicurando coerenza transazionale.

---

### 🔍 Variabili di Contesto e Configurazione

| Variabile                              | Scopo                                                                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `tx_id_bypass_enabled`                 | Parametro (`config.parameters`) che abilita il bypass completo: se `TRUE`, non viene generato né verificato un nuovo `tx_id`. |
| `app.bypass_tx_id_check`               | GUC di sessione: può essere usata per override temporanei del bypass senza cambiare il parametro globale.                     |
| `current_setting('dbops.tx_id', TRUE)` | Legge il valore di `tx_id` salvato in sessione, se presente; altrimenti solleva eccezione interna.                            |
| `script.uuid_nil()`                    | Funzione helper che restituisce l’UUID nil (`00000000-0000-0000-0000-000000000000`).                                          |

---

### ⚙️ Flusso di Esecuzione Dettagliato

1. **Verifica bypass globale**

   * Legge `config.parameters` per il parametro `tx_id_bypass_enabled`.
   * In caso di mancanza o di errore, logga via `fn_log_and_raise_error` e prosegue con bypass disabilitato.

2. **Override bypass a sessione**

   * Se il bypass non è già abilitato, prova a leggere `app.bypass_tx_id_check` dalla GUC di sessione.
   * Eventuali errori di lettura vengono ignorati (assume bypass disabilitato).

3. **Recupero `tx_id` di sessione**

   * Tenta `current_setting('dbops.tx_id', TRUE)` per ottenere un `tx_id` già presente in sessione.
   * In caso di errore o non esistenza, `v_session_tx_id` = `NULL`.

4. **Determinazione del nuovo `tx_id`**

   * **Bypass attivo**: usa `v_session_tx_id` se esistente, altrimenti `uuid_nil()`.
   * **Bypass disabilitato**:

     * **Se `v_session_tx_id` non è NULL**: verifica in `dbops.transaction_ids`.

       * Se esiste, lo riutilizza.
       * Se non esiste, logga warning (`W_TXID_NOT_REGISTERED`) e assegna `uuid_nil()`.
     * **Se `v_session_tx_id` è NULL**: genera uno nuovo con `dbops.fn_get_or_create_session_tx_id()`.

       * In caso di errori di generazione, logga errore (`E_TXID_GENERATION`) e usa `uuid_nil()`.

5. **Assegnazione a NEW\.tx\_id**

   ```plpgsql
   NEW.tx_id := v_new_tx_id;
   ```

   Garantisce che ogni riga inserita o aggiornata abbia sempre un `tx_id` valido secondo la logica centralizzata.

---

### 🔖 Esempio di Trigger DDL

```sql
DROP TRIGGER IF EXISTS trg_managed_tx_id ON my_schema.my_table;
CREATE TRIGGER trg_managed_tx_id
  BEFORE INSERT OR UPDATE
  ON my_schema.my_table
  FOR EACH ROW
  EXECUTE FUNCTION dbops.trgfn_tx_id_managed();
```

---

### 💡 Vantaggi Operativi

* **Centralizzazione logica**: nessuna duplicazione di codice di generazione/validazione del `tx_id` across tabelle.
* **Flessibilità**: gestisce bypass globali e di sessione per scenari di test, migrazione o debug.
* **Affidabilità**: verifica sempre l’esistenza del `tx_id` e assicura fallback pulito a `uuid_nil()`.
* **Tracciabilità avanzata**: associa ogni record al giusto `tx_id`, mantenendo coerenza con il registro centrale `transaction_ids`.

---

> 🧠 **“`trgfn_tx_id_managed` è il cuore della gestione transazionale in Zero ERP: garantisce consistenza, controlli configurabili e fallback sicuri, mantenendo la logica di correlazione centralizzata.”**
