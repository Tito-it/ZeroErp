## 📘 Documentazione Concettuale – Function `script.fn_log_and_raise_error`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
> - [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)    
> - [dbops.error_log](/dbzero/dbops/tabelle/error_log)    
>
> Approfondimenti funzioni:   
> - [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)     


La funzione **`script.fn_log_and_raise_error`** centralizza il flusso di gestione errori in PL/pgSQL: recupera testo, causa e soluzione dal catalogo dei messaggi, scrive un record nel log errori e quindi rialza un’eccezione con dettaglio e hint.

---

```sql
CREATE OR REPLACE FUNCTION script.fn_log_and_raise_error(
  p_area               text,          -- 'database' / 'backend' / 'frontend'
  p_function_name      text,          -- nome di trigger o funzione chiamante
  p_messaggio_errore_id bigint,       -- FK su config.messaggi_errore.id
  p_context            jsonb   DEFAULT '{}'::jsonb  -- payload di contesto
)
RETURNS void
LANGUAGE plpgsql
VOLATILE
AS $$
...implementazione...
$$;
```

### 🎯 Scopo Principale

* **Centralizzare la gestione errori** in un unico punto, evitando duplicazioni di codice e garantendo uniformità.
* **Log automatico**: registra sempre il contesto e la transazione prima di interrompere l’esecuzione.
* **Eccezioni contestuali**: fornisce `DETAIL` e `HINT` con causa e suggerimento di soluzione.

---

### 🔍 Parametri

| Parametro               | Tipo     | Descrizione                                                                          |
| ----------------------- | -------- | ------------------------------------------------------------------------------------ |
| `p_area`                | `text`   | Ambito di provenienza (`database`, `backend`, `frontend`, `job`, etc.)               |
| `p_function_name`       | `text`   | Nome del trigger/funzione o componente che ha rilevato l’errore                      |
| `p_messaggio_errore_id` | `bigint` | FK verso `config.messaggi_errore(id)`, specifica il codice e la lingua del messaggio |
| `p_context`             | `jsonb`  | Oggetto JSON con variabili, parametri e metadati utili per il debugging              |

---

### ⚙️ Flusso di Esecuzione

1. **Recupero del messaggio**

   ```plpgsql
   SELECT messaggio, causa, soluzione
     INTO v_messaggio, v_causa, v_soluzione
     FROM config.messaggi_errore
    WHERE id = p_messaggio_errore_id
      AND lingua = coalesce(current_setting('myapp.user_language', true), 'it');
   ```
2. **Scrittura nel log errori**

   ```plpgsql
   INSERT INTO dbops.error_log(
     occurred_at, area, function_name,
     messaggio_errore_id, context, tx_id
   ) VALUES (
     now(), p_area, p_function_name,
     p_messaggio_errore_id, p_context,
     (md5(txid_current()::text))::uuid
   );
   ```
3. **Rialzo dell’eccezione**

   ```plpgsql
   RAISE EXCEPTION '%', v_messaggio
     USING
       DETAIL = coalesce(v_causa, ''),
       HINT   = coalesce(v_soluzione, '');
   ```

   L’eccezione interrompe l’esecuzione, mostrando il messaggio principale, il dettaglio della causa e l’hint di soluzione.

---

### 🔒 Comportamento e Side Effect

* **Volatile**: il comportamento dipende dallo stato e modifica la tabella di log.
* **Transazionale**: `tx_id` consente di collegare errori e audit via `dbops.audit_log` o altre entità.
* **Contesto**: salva il payload JSON, utile per ricostruire lo stato al momento dell’errore.

---

### ⚙️ Esempi di Utilizzo

1. **In un trigger PL/pgSQL**

   ```plpgsql
   IF NEW.amount < 0 THEN
     PERFORM script.fn_log_and_raise_error(
       'database', TG_NAME, 1001,
       jsonb_build_object('id', OLD.id, 'amount', NEW.amount)
     );
   END IF;
   ```

2. **In una procedura lato backend**

   ```plpgsql
   BEGIN
     -- logica di business...
   EXCEPTION WHEN others THEN
     PERFORM script.fn_log_and_raise_error(
       'backend', 'process_orders', 2002,
       jsonb_build_object('payload', to_jsonb(order_data))
     );
   END;
   ```

---

### 💡 Vantaggi Operativi

* **Uniformità**: un solo standard per logging e gestione eccezioni.
* **Tracciabilità completa**: messaggio, causa, contesto e transazione sono collegati.
* **Manutenibilità**: modifiche ai testi di errore avvengono centralmente in `config.messaggi_errore`.
* **Supporto al debug**: hint e cause dettagliate guidano l’operatore verso la soluzione.

---

> 🧠 **“Centralizzare logica di error handling e log in una funzione dedicata semplifica il codice, migliora la tracciabilità e accelera le attività di debugging.”**
