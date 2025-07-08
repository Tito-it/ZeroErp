## 📘 Documentazione Concettuale – Funzione `script.trgfn_prevent_modification_generic()`

> 👀 **Vedi anche**
>
> Approfondimento funzioni :    
> - [script.fn_log_and_raise_error](\dbzero\script\funzioni\fn_log_and_raise_error.)    


La trigger function **`script.trgfn_prevent_modification_generic()`** impedisce modifiche o cancellazioni sui record di tabelle di audit (o altre tabelle protette), sollevando un’eccezione centralizzata tramite `fn_log_and_raise_error`.

---

### 🎯 Scopo Principale

* **Proteggere dati di audit**
  Garantire l’inalterabilità delle cronologie storiche registrate in tabelle dedicate (es. `config.parameters_audit`).
* **Centralizzare la gestione degli errori**
  Usare un wrapper di logging e exception unificato per fornire messaggi coerenti e tracce in log.

---

### 🔍 Parametri di Input

Questa funzione **non** riceve parametri espliciti: utilizza le variabili di contesto PL/pgSQL:

| Variabile       | Descrizione                                                                   |
| --------------- | ----------------------------------------------------------------------------- |
| `TG_TABLE_NAME` | Nome della tabella su cui è stato invocato il trigger.                        |
| `TG_OP`         | Tipo di operazione che ha attivato il trigger (`INSERT`, `UPDATE`, `DELETE`). |

---

### ⚙️ Flusso di Esecuzione

1. **Chiamata dal trigger**
   Eseguita `BEFORE UPDATE` o `BEFORE DELETE` sulla tabella protetta.
2. **Sollevamento dell’eccezione**
   Invoca:

   ```plpgsql
   PERFORM script.fn_log_and_raise_error(
     'database',                             -- canale log
     'trgfn_prevent_parameters_audit_modification', -- nome del trigger/contesto
     'E_TABELLA_OP_NON_CONSENTITA',          -- codice messaggio (E=Error)
     jsonb_build_object(
       'nome_tabella', TG_TABLE_NAME,
       'trigger_op',    TG_OP
     ),                                       -- contesto JSON per il messaggio
     TG_TABLE_NAME::text,
     TG_OP::text
   );
   ```

   La funzione `fn_log_and_raise_error` logga l’evento e lancia un `RAISE EXCEPTION` con un messaggio tradotto da tabella `config.messaggi_errore`.
3. **Prevenzione operazione**
   Poiché l’eccezione interrompe l’operazione, nessuna modifica viene applicata.

---

### 🔖 Definizione SQL

```sql
CREATE OR REPLACE FUNCTION script.trgfn_prevent_modification_generic()
  RETURNS trigger
  LANGUAGE plpgsql
AS $function$
BEGIN
  PERFORM script.fn_log_and_raise_error(
    'database',
    'trgfn_prevent_parameters_audit_modification',
    'E_TABELLA_OP_NON_CONSENTITA',
    jsonb_build_object(
      'nome_tabella', TG_TABLE_NAME,
      'trigger_op',   TG_OP
    ),
    TG_TABLE_NAME::text,
    TG_OP::text
  );
END;
$function$;

COMMENT ON FUNCTION script.trgfn_prevent_modification_generic() IS
  'Trigger function che blocca UPDATE e DELETE su tabelle protette, sollevando errore tramite fn_log_and_raise_error.';
```

---

### 🚀 Applicazione del Trigger

Per proteggere una tabella (es. `config.parameters_audit`):

```sql
DROP TRIGGER IF EXISTS trg_prevent_mod_parameters_audit ON config.parameters_audit;

CREATE TRIGGER trg_prevent_mod_parameters_audit
  BEFORE UPDATE OR DELETE
  ON config.parameters_audit
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_prevent_modification_generic();
```

---

### 💡 Vantaggi Operativi

* **Sicurezza dei dati**: impedisce involontarie cancellazioni o modifiche.
* **Consistenza dei messaggi**: utilizza un sistema di logging/exception centralizzato per coerenza.
* **Riutilizzabilità**: la stessa funzione può proteggere più tabelle di audit o log.

---

> 🧠 **“Centralizzare la protezione dei dati critici in una trigger function riutilizzabile assicura sicurezza, trasparenza e facilità di manutenzione.”**
