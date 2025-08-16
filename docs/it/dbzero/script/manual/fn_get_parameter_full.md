## 📘 Documentazione Concettuale – Funzione `script.fn_get_parameter_full`


> 👀 **Vedi anche**  
>
> Approfondimento Tabelle:   
>
> * [config.parameters](/dbzero/config/tabelle/parameters)      
> * [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)      
>
> Approfondimento funzioni :    
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)     



La funzione **`script.fn_get_parameter_full(p_code TEXT, p_tenant_id INTEGER DEFAULT NULL, p_user_id INTEGER DEFAULT NULL, p_session_key TEXT DEFAULT NULL, p_function_name TEXT DEFAULT NULL) RETURNS TEXT`** restituisce il valore di un parametro, applicando una catena di override con priorità:

1. **Function** (`p_function_name`)
2. **Session** (`p_session_key`)
3. **User** (`p_user_id`)
4. **Tenant** (`p_tenant_id`)
5. **Default** (`config.parameters.default_value`)

Se il parametro non esiste, viene loggato un errore e sollevata un’eccezione.

---

### 🎯 Scopo Principale

* **Ricerca safe del parametro**
  Verificare l’esistenza del parametro in `config.parameters` e recuperare il suo `default_value`.
* **Override gerarchico**
  Cercare eventuali override in `config.parameter_overrides` secondo la priorità: function → session → user → tenant.
* **Centralizzazione della logica**
  Un’unica funzione per gestire la complessità degli override, evitando duplicazioni nell’applicazione.
* **Gestione degli errori**
  Se `p_code` non è presente in `config.parameters`, viene chiamato `script.fn_log_and_raise_error` con codice `ERRORE_PARAMETRI_TABELLA`.

---

### 🔍 Parametri di Input

| Nome              | Tipo      | Default | Descrizione                                                  |
| ----------------- | --------- | ------- | ------------------------------------------------------------ |
| `p_code`          | `TEXT`    | —       | Codice del parametro da cercare in `config.parameters.code`. |
| `p_tenant_id`     | `INTEGER` | `NULL`  | ID del tenant per override di scope `tenant`.                |
| `p_user_id`       | `INTEGER` | `NULL`  | ID dell’utente (es. da Django) per override di scope `user`. |
| `p_session_key`   | `TEXT`    | `NULL`  | Chiave di sessione per override di scope `session`.          |
| `p_function_name` | `TEXT`    | `NULL`  | Nome della funzione per override di scope `function`.        |

---

### ⚙️ Flusso Logico

1. **Recupero parametro base**

   ```plpgsql
   SELECT id, default_value
     INTO v_param_id, v_default
     FROM config.parameters
    WHERE code = p_code;
   IF NOT FOUND THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       'fn_get_parameter_full',
       'ERRORE_PARAMETRI_TABELLA',
       jsonb_build_object(
         'codice_parametro', p_code,
         'nome_tabella',      'config.parameters'
       ),
       COALESCE(p_code, 'NULL')
     );
   END IF;
   ```
2. **Ricerca override**

   ```plpgsql
   SELECT overridden_value
     INTO v_override
     FROM config.parameter_overrides
    WHERE parameter_id = v_param_id
      AND (
            (function_name   IS NOT NULL AND function_name   = p_function_name)
         OR (session_key     IS NOT NULL AND session_key     = p_session_key)
         OR (user_id         IS NOT NULL AND user_id         = p_user_id)
         OR (tenant_id       IS NOT NULL AND tenant_id       = p_tenant_id)
          )
    ORDER BY CASE
               WHEN function_name   = p_function_name THEN 1
               WHEN session_key     = p_session_key   THEN 2
               WHEN user_id         = p_user_id       THEN 3
               WHEN tenant_id       = p_tenant_id     THEN 4
               ELSE 5
             END
    LIMIT 1;
   ```
3. **Restituzione del valore**

   ```plpgsql
   IF FOUND THEN
     RETURN v_override;
   ELSE
     RETURN v_default;
   END IF;
   ```

---

### 🔒 Valore di Ritorno

* **`TEXT`**
  Valore dell’override più specifico trovato, o in assenza di override il `default_value` originale.

---

### 💡 Vantaggi Operativi

* **Flessibilità multi-scope**
  Supporta override a livello di funzione, sessione, utente e tenant.
* **Sicurezza**
  Log e error handling centralizzato via `fn_log_and_raise_error` per parametri mancanti.
* **Semplificazione**
  Un’unica funzione evita di scrivere query multiple in applicazione.
* **Manutenibilità**
  Modifiche alla catena di override possono essere gestite in un solo punto.

---

### 🔖 Firma SQL

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_full(
  p_code          TEXT,
  p_tenant_id     INTEGER DEFAULT NULL,
  p_user_id       INTEGER DEFAULT NULL,
  p_session_key   TEXT    DEFAULT NULL,
  p_function_name TEXT    DEFAULT NULL
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
-- implementazione come sopra
$$;
```

> 🧠 **“Utilizzando `fn_get_parameter_full`, l’applicazione ottiene in modo deterministico il valore corretto di un parametro, rispettando una gerarchia di override chiaramente definita.”**
