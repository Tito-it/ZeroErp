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
  p_tx_id          UUID,                       -- transaction id per correlazione audit (ammesso NULL)
  VARIADIC p_valori TEXT[]                     -- valori da sostituire a '%s' nel template messaggio
)
RETURNS VOID
LANGUAGE plpgsql
VOLATILE
AS $$
...implementazione con fn_log_error_only + fn_get_messaggio + RAISE...
$$;
```

> ⚠️ **Breaking change 23-04-2026**: la firma ha acquisito il parametro
> fisso `p_tx_id UUID` al 5° posto (prima del `VARIADIC`). Ogni caller
> che passava direttamente i valori dopo `p_context` va aggiornato:
> inserire `NEW.tx_id` (trigger) o `NULL::uuid` (caller generico) come 5°
> argomento. Migrazione che ha introdotto il cambio:
> `20260423-02-update-fn-get-messaggio-e-log-raise-fallback-lingua`.

### 🎯 Scopo Principale

(last review 24-04-2026)

* **Entrypoint unificato** per error handling: evita duplicazioni di log e raise in trigger, procedure e funzioni.
* **Logging delegato a `fn_log_error_only`** (post 23-04-2026): la fn non scrive direttamente via `dblink_exec`, ma invoca `script.fn_log_error_only(...)` che a sua volta usa `dblink` su connessione permanente (`fn_ensure_logconn`) per isolare il log dall'eventuale rollback della sessione principale.
* **Escalation immediata**: rialza l'eccezione con `DETAIL` e `HINT` recuperati dalla tabella dei messaggi con fallback lingua.

---

### Parametri

| Parametro         | Tipo     | Descrizione                                                                        |
| ----------------- | -------- | ---------------------------------------------------------------------------------- |
| `p_area`          | `TEXT`   | Ambito di origine (`database`, `backend`, `frontend`, `job`, etc.)                 |
| `p_function_name` | `TEXT`   | Nome del trigger/funzione o componente chiamante *(vedi nota 1)*                   |
| `p_error_code`    | `TEXT`   | Codice del messaggio da cercare in `config.messaggi_errore.codice`                 |
| `p_context`       | `JSONB`  | Contesto in formato JSONB (es. parametri, utente, stack trace)                     |
| `p_tx_id`         | `UUID`   | Transaction id per correlazione audit *(post 23-04-2026, vedi nota 2)*             |
| `p_valori`        | `TEXT[]` | Array variadico di valori per sostituire i placeholder `%s` nel template messaggio |

**Note**:

1. **Cast `TG_NAME::text` nei trigger**: la variabile speciale `TG_NAME` e' di tipo `name` (non `text`). Senza cast esplicito la function resolution di PostgreSQL fallisce con `la funzione script.fn_log_and_raise_error(..., name, ...) non esiste`. Anche se in alcuni contesti l'assignment cast implicito salva, nei chiamanti con molti parametri (specialmente con variadic) **il cast e' obbligatorio**.
2. **`p_tx_id` per correlazione audit**: nei trigger passare `NEW.tx_id` (colonna audit standard); in caller non-trigger dove non c'e' un tx_id disponibile passare `NULL::uuid`. La fn gestisce il NULL senza errori.

---

### Flusso di Esecuzione (post 23-04-2026)

1. **Delega del logging a `fn_log_error_only`**

   Il logging via dblink e' delegato a `script.fn_log_error_only`,
   che internamente invoca `fn_ensure_logconn` + `dblink_exec`.

   ```plpgsql
   PERFORM script.fn_log_error_only(
       p_area, p_function_name, p_error_code,
       p_context, p_tx_id, VARIADIC p_valori
   );
   ```

2. **Risoluzione lingua di sessione**

   ```plpgsql
   v_lang := coalesce(current_setting('myapp.user_language', true), 'it');
   ```

3. **Recupero messaggio con fallback lingua**

   Il **messaggio testuale** e' delegato a `script.fn_get_messaggio`,
   che applica il fallback lingua IT internamente (migration
   `20260423-02-01`).

   ```plpgsql
   v_msg := script.fn_get_messaggio(p_error_code, NULL, v_lang);
   ```

4. **Recupero causa/soluzione con fallback IT inline**

   Single-query: preferisci `v_lang`, ricadi su `'it'` se manca.

   ```plpgsql
   SELECT causa, soluzione
     INTO v_detail, v_hint
     FROM config.messaggi_errore
    WHERE codice = p_error_code
      AND lingua IN (v_lang, 'it')
    ORDER BY (lingua = v_lang) DESC
    LIMIT 1;
   ```

   **Semantica row-atomic**: se la riga EN esiste ma ha `causa=NULL`
   e/o `soluzione=NULL`, la fn **mantiene i NULL della riga EN** senza
   mescolarli con i valori IT. E' intenzionale: chi legge gli errori
   non deve vedere `DETAIL` in IT e `HINT` in EN per lo stesso
   errore. La traduzione si considera "completa" solo quando tutti i
   campi sono popolati.

   Se non c'e' riga ne' in `v_lang` ne' in `'it'`, `v_detail` e
   `v_hint` restano NULL e il RAISE usa stringa vuota (coalesce).

5. **Formattazione del messaggio con VARIADIC**

   ```plpgsql
   IF array_length(p_valori, 1) IS NOT NULL THEN
       v_msg := format(v_msg, VARIADIC p_valori);
   END IF;
   ```

6. **Sollevamento dell'eccezione con DETAIL/HINT localizzati**

   ```plpgsql
   RAISE EXCEPTION '%', v_msg
       USING DETAIL = coalesce(v_detail, ''),
             HINT   = coalesce(v_hint,   '');
   ```

---

### Comportamenti e Side Effects

* **Volatile**: invoca `dblink_exec`, quindi non idempotente.
* **Connessione permanente**: `logconn` gestita da `script.fn_ensure_logconn()` per evitare overhead di connessioni multiple.
* **Separazione transazionale**: l’INSERT remoto non viene rollbackato insieme alla sessione principale.

---

### Esempi di Utilizzo (post 23-04-2026)

1. **Trigger PL/pgSQL con `NEW.tx_id` + placeholder VARIADIC**

   ```plpgsql
   IF NEW.status = 'ERROR' THEN
       PERFORM script.fn_log_and_raise_error(
           'database',
           TG_NAME::text,                              -- cast obbligatorio
           'ERR_INVALID_STATUS',
           jsonb_build_object('id', NEW.id),
           NEW.tx_id,                                  -- p_tx_id UUID
           OLD.status::text, NEW.status::text          -- VARIADIC %s
       );
   END IF;
   ```

2. **Funzione/procedura senza tx_id di riga (usa NULL::uuid)**

   ```plpgsql
   BEGIN
       -- operazioni...
   EXCEPTION WHEN OTHERS THEN
       PERFORM script.fn_log_and_raise_error(
           'backend',
           'sync_data',
           'ERR_TIMEOUT',
           jsonb_build_object('user', current_user),
           NULL::uuid,                                 -- p_tx_id NULL ammesso
           now()::text                                 -- VARIADIC %s
       );
   END;
   ```

3. **Caller senza placeholder VARIADIC (solo messaggio statico)**

   ```plpgsql
   PERFORM script.fn_log_and_raise_error(
       'database',
       TG_NAME::text,
       'E_OPERAZIONE_NON_AMMESSA',
       jsonb_build_object('versione_id', NEW.id),
       NEW.tx_id
       -- p_valori VARIADIC omesso: il messaggio non ha %s
   );
   ```

---

### Vantaggi Operativi

* **Resilienza dei log**: l'uso di dblink isola il logging dall'eventuale rollback.
* **Flessibilità**: placeholder `%s` e `p_valori` rendono i messaggi dinamici e contestuali.
* **Manutenibilità**: modifiche ai messaggi avvengono solo in `config.messaggi_errore`.
* **Tracciabilità completa**: contesto, transazione e multilingua integrate nel flusso.
* **Rollout incrementale traduzioni** (post 23-04-2026): il fallback
  lingua IT su messaggio, causa e soluzione permette di aggiungere
  traduzioni EN (o altre lingue) un codice alla volta, senza dover
  tradurre tutti i ~390 codici errore in un solo commit. La semantica
  row-atomic evita mix di lingue nello stesso errore.

---

> **“Una funzione centralizzata che combina dblink per log persistente e raise exception con template dinamici semplifica error handling, migliorando la robustezza del sistema.”**
