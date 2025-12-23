## 📘 Documentazione Concettuale – Funzione `script.fn_get_parameter_full()`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle:**
>
> * [config.parameters](/dbzero/config/tabelle/parameters)   
> * [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)   
>
> **Approfondimento funzioni:**
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

---

La funzione **`script.fn_get_parameter_full(...) RETURNS TEXT`** restituisce il valore di un parametro applicando:

* **default** da `config.parameters.default_value`
* eventuali **override** da `config.parameter_overrides`

con una **precedenza deterministica**.

---

### 🎯 Scopo Principale

(latest update 21-12-25)
* **Ricerca safe del parametro**
  Verifica l’esistenza del parametro in `config.parameters` e recupera `id` + `default_value`.

* **Override gerarchico**
  Cerca un override in `config.parameter_overrides` secondo la precedenza implementata.

* **Centralizzazione**
  Un unico punto di verità per la risoluzione parametri, evitando duplicazioni nel codice DB/app.

* **Gestione errori**
  Se `p_code` non esiste in `config.parameters`, logga (`ERRORE_PARAMETRI_TABELLA`) e solleva eccezione.

---

### 🔍 Firma e Parametri di Input (coerenti con il codice attuale)

```sql
script.fn_get_parameter_full(
  p_code text,
  p_tenant_id integer DEFAULT NULL,
  p_django_user_id integer DEFAULT NULL,
  p_group_ids integer[] DEFAULT NULL,
  p_session_key text DEFAULT NULL,
  p_function_name text DEFAULT NULL
) RETURNS text
```

| Nome               | Tipo        | Default | Descrizione                                  |
| ------------------ | ----------- | ------- | -------------------------------------------- |
| `p_code`           | `text`      | —       | Codice parametro (`config.parameters.code`). |
| `p_tenant_id`      | `integer`   | `NULL`  | Override scope tenant.                       |
| `p_django_user_id` | `integer`   | `NULL`  | Override scope utente (Django).              |
| `p_group_ids`      | `integer[]` | `NULL`  | Override scope gruppi (Django groups).       |
| `p_session_key`    | `text`      | `NULL`  | Override scope sessione.                     |
| `p_function_name`  | `text`      | `NULL`  | Override scope funzione/chiamante.           |

---

### ⚙️ Precedenza Override (IMPORTANTE)

La funzione seleziona **al massimo un override** e, in caso di più match, applica questa precedenza **come da ORDER BY nel codice**:

1. **User** (`django_user_id`)
2. **Group** (`django_group_id IN p_group_ids`)
3. **Tenant** (`tenant_id`)
4. **Session** (`session_key`)
5. **Function** (`function_name`)
6. **Default** (`config.parameters.default_value`)

> 📌 Questa gerarchia è quella effettivamente implementata: se vuoi un ordine diverso (es. function sopra user), va cambiato l’`ORDER BY`.

---

### 🧠 Flusso Logico

1. **Recupero parametro base** (`id`, `default_value`) da `config.parameters`.
2. Se non trovato:

   * `script.fn_log_and_raise_error(..., 'ERRORE_PARAMETRI_TABELLA', ...)`
   * `RAISE EXCEPTION ...` (ERRCODE `22023`).
3. **Ricerca override** su `config.parameter_overrides` filtrando per `parameter_id` e per almeno uno tra:

   * `django_user_id = p_django_user_id`
   * `django_group_id = ANY(p_group_ids)`
   * `tenant_id = p_tenant_id`
   * `session_key = p_session_key`
   * `function_name = p_function_name`
4. Se trovato override ⇒ ritorna `overridden_value`, altrimenti ritorna `default_value`.

---

### 🔒 Valore di Ritorno

* **`TEXT`**: valore override più specifico trovato, o `default_value` se nessun override applicabile.

---

### 💡 Note Operative

* **Multi‑scope reale:** supporta contemporaneamente user/group/tenant/session/function.
* **Determinismo:** l’`ORDER BY` definisce una precedenza chiara anche quando più override matchano.
* **Performance:** tipicamente usata frequentemente; utile mantenere indici adeguati su `config.parameter_overrides` (per `parameter_id` e colonne scope).

---

> 🧠 **“`fn_get_parameter_full` risolve in modo deterministico il valore di un parametro applicando override multi‑scope (user → group → tenant → session → function), mantenendo logging ed error handling centralizzati.”**

{% include-markdown "signature-core.md" %}
