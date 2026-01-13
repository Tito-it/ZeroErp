## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_or_create_session_tx_id()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
>
> * [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids)      
>
> Approfondimento funzioni :    
>
> * [dbops.fn_generate_tx_id](/dbzero/dbops/funzioni/fn_generate_tx_id)    
> * [script.uuid_nil](/dbzero/script/funzioni/uuid_nil)    
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn)    

La funzione **`dbops.fn_get_or_create_session_tx_id()`** fornisce un **UUID di transazione** persistente per l’intera sessione database, generandone uno nuovo solo se non già impostato. Questo meccanismo garantisce che tutte le operazioni eseguite nella medesima connessione possano condividere lo stesso **`tx_id`**, semplificando log, tracciabilità e rollback in scenari complessi.

---

### 🎯 Scopo Principale

(latest review 10-01-26)
* **Unicità per sessione**: restituisce un `tx_id` costante per la durata della connessione, evitando chiamate ripetute a generatori esterni.
* **Fallback sicuro**: in caso di errori di connessione o in contesti di migrazione/test, restituisce un UUID “nil” per non bloccare i processi.
* **Contesto centralizzato**: memorizza il `tx_id` in una GUC di sessione (`dbops.tx_id`) per accessi successivi.

---

### 🔍 Parametri di Input

Questa funzione **non** richiede parametri. Tutta la logica utilizza variabili di sessione e la funzione di generazione:

| Parametro | Tipo | Default | Descrizione                                                   |
| --------- | ---- | ------- | ------------------------------------------------------------- |
| *nessuno* | –    | –       | La funzione auto-determina se creare o restituire il `tx_id`. |

---

### ⚙️ Flusso di Esecuzione Dettagliato

1. **Verifica connessione di logging**

   ```plpgsql
   PERFORM script.fn_ensure_logconn();
   ```

   Garantisce che il database sia pronto per eventuali chiamate `dblink` di audit o generazione remota.

2. **Lettura `dbops.tx_id` dalla sessione**

   ```plpgsql
   v_tx_id := current_setting('dbops.tx_id', TRUE)::UUID;
   ```

   * Se esiste e vale un UUID, lo restituisce subito.
   * In caso di eccezione (non settato), `v_tx_id` rimane `NULL`.

3. **Generazione on‑demand tramite `dblink`**

   ```plpgsql
   SELECT tx_id
     INTO v_tx_id
     FROM dblink(
       current_setting('dblink.log_connection', TRUE),
       $gen$
         SELECT dbops.fn_generate_tx_id(
           'dbops.fn_get_or_create_session_tx_id',
           jsonb_build_object('source','fn_get_or_create')
         )
       $gen$
     ) AS t(tx_id UUID);
   ```

   * La chiamata `dblink` esegue la function remota per creare e registrare un nuovo `tx_id`.
   * Imposta la GUC di sessione:

     ```plpgsql
     PERFORM set_config('dbops.tx_id', v_tx_id::text, TRUE);
     ```
   * **Casistiche di fallimento**: su qualunque eccezione di `dblink`, cattura l’errore e assegna:

     ```plpgsql
     v_tx_id := script.uuid_nil();
     ```

     restituendo un UUID “nil” (`00000000-0000-0000-0000-000000000000`).

4. **Restituzione del `tx_id`**

   ```plpgsql
   RETURN v_tx_id;
   ```

---


---

### 🚀 Esempio di Utilizzo

```sql
-- Prima invocazione in sessione nuova:
SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id;
-- Restituisce e memorizza un nuovo UUID.

-- Invocazione successiva nella medesima sessione:
SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id;
-- Restituisce lo stesso UUID senza creare nuovi record.
```

---

### 💡 Vantaggi e Considerazioni

* **Tracciabilità coerente**: tutte le chiamate in sessione condividono lo stesso `tx_id`, semplificando log e correlazione.
* **Performance**: riduce chiamate ridondanti a `fn_generate_tx_id`.
* **Fallback controllato**: restituisce `uuid_nil()` in caso di errori, utile in test o migrazioni dove non si desidera popolare la tabella `transaction_ids`.
* **Estendibilità**: può essere temporaneamente disattivata impostando manualmente `dbops.tx_id` su un valore predefinito o `000...0`, evitando side‑effect in contesti speciali.

---

> 🧠 **“`fn_get_or_create_session_tx_id` garantisce un unico punto di controllo per il transaction ID di sessione, unendo performance, sicurezza e fallback affidabile.”**
