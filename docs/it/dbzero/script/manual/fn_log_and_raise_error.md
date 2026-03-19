## 📘 Documentazione Concettuale – Function `script.fn_log_and_raise_error`

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)    
> [dbops.error_log](/dbzero/dbops/tabelle/error_log)    
>
Approfondimenti funzioni:   
> [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) *(solo log non solleva eccezioni)*  
> [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)     
> [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn)     


La funzione **`script.fn_log_and_raise_error`** unifica logging ed escalation di errori in PL/pgSQL, utilizzando l’estensione **dblink** per inserire record di log in una sessione separata e garantire commit immediato, quindi solleva un’eccezione con messaggio, dettaglio e hint.

---

```sql
CREATE OR REPLACE FUNCTION script.fn_log_and_raise_error(
  p_area           TEXT,                       -- 'database' / 'backend' / 'frontend' / 'job'
  p_function_name  TEXT,                       -- nome di trigger o funzione chiamante
  p_error_code     TEXT,                       -- codice testuale di messaggio (config.messaggi_errore.codice)
  p_context        JSONB,                      -- payload di contesto (parametri, variabili, metadata)
  VARIADIC p_valori TEXT[]                     -- valori da sostituire a '%s' nel template messaggio
)
RETURNS VOID
LANGUAGE plpgsql
VOLATILE
AS $$
...implementazione completa con dblink_exec...
$$;
```
### 🎯 Scopo Principale
(last review 28-12-25)
* **Entrypoint unificato** per error handling: evita duplicazioni di log e raise in trigger, procedure e funzioni.
* **Logging remoto sicuro**: usa `dblink_exec` su connessione permanente fornita da `script.fn_ensure_logconn()`, per isolare il log dall’eventuale rollback della sessione principale.
* **Escalation immediata**: rialza l’eccezione con `DETAIL` e `HINT` recuperati dalla tabella dei messaggi.

---

### Parametri

| Parametro         | Tipo     | Descrizione                                                                        |
| ----------------- | -------- | ---------------------------------------------------------------------------------- |
| `p_area`          | `TEXT`   | Ambito di origine (`database`, `backend`, `frontend`, `job`, etc.)                 |
| `p_function_name` | `TEXT`   | Nome del trigger/funzione o componente chiamante                                   |
| `p_error_code`    | `TEXT`   | Codice del messaggio da cercare in `config.messaggi_errore.codice`                 |
| `p_context`       | `JSONB`  | Contesto in formato JSONB (es. parametri, utente, stack trace)                     |
| `p_valori`        | `TEXT[]` | Array variadico di valori per sostituire i placeholder `%s` nel template messaggio |

---

### Flusso di Esecuzione

1. **Assicuro connessione dblink**

   ```plpgsql
   PERFORM script.fn_ensure_logconn();
   ```

2. **Recupero messaggio e metadati**

   ```plpgsql
   SELECT id, messaggio, causa, soluzione
     INTO v_id, v_messaggio, v_causa, v_soluzione
   FROM config.messaggi_errore
   WHERE codice = p_error_code
     AND lingua = v_lingua;
   ```

   Se non trovato, imposta testo, causa e soluzione di default indicativi.

3. **Formattazione del messaggio**

   ```plpgsql
   IF array_length(p_valori,1) IS NOT NULL THEN
     v_messaggio := format(v_messaggio, VARIADIC p_valori);
   END IF;
   ```

4. **Preparazione dell’INSERT remoto**

   ```plpgsql
   sql_text :=
     'INSERT INTO dbops.error_log(occurred_at, area, function_name,' ||
     ' messaggio_errore_id, context, tx_id) VALUES (' ||
     'now(), ' || quote_literal(p_area) || ', ' || quote_literal(p_function_name) || ', ' ||
     coalesce(v_id::text,'NULL') || ', ' || quote_literal(v_context::text) || '::jsonb, ' ||
     quote_literal(md5(txid_current()::text)) || '::uuid' || ');';
   ```

5. **Esecuzione tramite dblink**

   ```plpgsql
   PERFORM dblink_exec('logconn', sql_text);
   ```

6. **Sollevamento dell’eccezione**

   ```plpgsql
   RAISE EXCEPTION '%', coalesce(v_messaggio, '[Errore sconosciuto]')
     USING DETAIL = coalesce(v_causa,''),
           HINT   = coalesce(v_soluzione,'');
   ```

---

### Comportamenti e Side Effects

* **Volatile**: invoca `dblink_exec`, quindi non idempotente.
* **Connessione permanente**: `logconn` gestita da `script.fn_ensure_logconn()` per evitare overhead di connessioni multiple.
* **Separazione transazionale**: l’INSERT remoto non viene rollbackato insieme alla sessione principale.

---

### Esempi di Utilizzo

1. **Trigger PL/pgSQL con placeholder**

   ```plpgsql
   IF NEW.status = 'ERROR' THEN
     PERFORM script.fn_log_and_raise_error(
       'database', TG_NAME, 'ERR_INVALID_STATUS',
       jsonb_build_object('id', OLD.id),
       OLD.status, NEW.status
     );
   END IF;
   ```

2. **Procedure backend**

   ```plpgsql
   BEGIN
     -- operazioni...
   EXCEPTION WHEN OTHERS THEN
     PERFORM script.fn_log_and_raise_error(
       'backend', 'sync_data', 'ERR_TIMEOUT',
       jsonb_build_object('user', current_user),
       now()::text
     );
   END;
   ```

---

### Vantaggi Operativi

* **Resilienza dei log**: l’uso di dblink isola il logging dall’eventuale rollback.
* **Flessibilità**: placeholder `%s` e `p_valori` rendono i messaggi dinamici e contestuali.
* **Manutenibilità**: modifiche ai messaggi avvengono solo in `config.messaggi_errore`.
* **Tracciabilità completa**: contesto, transazione e multilingua integrate nel flusso.

---

> **“Una funzione centralizzata che combina dblink per log persistente e raise exception con template dinamici semplifica error handling, migliorando la robustezza del sistema.”**
