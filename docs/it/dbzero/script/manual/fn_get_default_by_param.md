## 📘 Documentazione Concettuale – Funzione `script.fn_get_default_by_param()`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle:**
>
> * [config.parameters](/dbzero/config/tabelle/parameters)   
> * [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)   
>
> **Approfondimento funzioni:**
>
> * [script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)    
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)    

---

### 🎯 Scopo Principale

(latest update 21-12-25)
Recuperare in modo dinamico un valore (tipicamente una **PK**) da una tabella qualsiasi, basandosi su un **codice parametro**.

La funzione:

1. Legge il **valore testuale** del parametro (`p_param_code`) tramite `script.fn_get_parameter_full()`.
2. Determina dinamicamente la **colonna PK** della tabella target (`p_table_schema.p_table_name`) interrogando il catalogo di sistema.
3. Esegue una **query dinamica** per ricavare l’ID:
   `SELECT pk FROM schema.tabella WHERE filter_column::text = param_value LIMIT 1`
   e restituisce il valore sempre come `TEXT`.
4. Se non trova la PK (o non trova record), registra l’errore e solleva `E_DEFAULT_ERRATO` con `script.fn_log_and_raise_error()`.

---

### 🔗 Collegamenti

* **`script.fn_get_parameter_full`** – risolve il valore di filtro (stringa) usando default + override.
* **`script.fn_log_and_raise_error`** – logging + raise error standardizzato (`E_DEFAULT_ERRATO`).
* **Cataloghi PG:** `pg_index`, `pg_class`, `pg_namespace`, `pg_attribute` – usati per ricavare il nome della colonna PK.

---

### 🔍 Parametri di Input

| Nome              | Tipo   | Descrizione                                                               |
| ----------------- | ------ | ------------------------------------------------------------------------- |
| `p_table_schema`  | `text` | Schema tabella target (es. `config`).                                     |
| `p_table_name`    | `text` | Nome tabella target (es. `stati`).                                        |
| `p_filter_column` | `text` | Colonna di filtro (es. `codice_iso3`).                                    |
| `p_param_code`    | `text` | Codice parametro in `config.parameters.code` (es. `state_code_iso3`).     |
| `p_function_name` | `text` | Contesto/funzione chiamante (usato nei log e nella risoluzione override). |

---

### 🔒 Valore di Ritorno

* **`TEXT`**: il valore della PK (o identificativo) trovato.
  Il chiamante può fare cast a `INTEGER`, `UUID`, ecc.

---

### ⚙️ Flusso Logico (coerente con l’implementazione attuale)

 **1️⃣ Risoluzione del valore parametro**

La funzione usa `script.fn_get_parameter_full()` passando:

* `p_code = p_param_code`
* `p_session_key = current_setting('app.session_key', true)`
* `p_function_name = p_function_name`
* `p_group_ids = NULL::integer[]` (non gestiti in questa funzione)

Esempio (call-site reale):

```plpgsql
v_param_val := script.fn_get_parameter_full(
  p_param_code,
  NULL,
  NULL,
  NULL::integer[],
  current_setting('app.session_key', true),
  p_function_name
);
```

> 📌 Nota: l’uso posizionale richiede di rispettare l’ordine dei parametri. Se in futuro la firma evolvesse, è consigliato usare **named parameters**.

---

 **2️⃣ Identificazione della PK della tabella target**

La funzione ricava il nome della colonna PK dalla primary key della tabella target; se non esiste PK, logga e solleva `E_DEFAULT_ERRATO`.

---

 **3️⃣ Lookup dinamico della riga**

Esegue una query parametrizzata (anti-injection sul valore):

```plpgsql
EXECUTE format(
  'SELECT %I::text FROM %I.%I WHERE %I::text = $1 LIMIT 1',
  v_pk_col, p_table_schema, p_table_name, p_filter_column
)
INTO v_lookup_id
USING v_param_val;
```

Se `v_lookup_id` è `NULL`, log + raise `E_DEFAULT_ERRATO`.

---

### 💡 Note Operative

* **Sicurezza:** la parte variabile nel `WHERE` usa `USING v_param_val` (parametro) e riduce rischi di injection sul valore.
* **Limite:** ritorna sempre un solo valore (`LIMIT 1`). Se la tabella non garantisce unicità sul filtro, la scelta è non deterministica.
* **Uso tipico:** risolvere default tecnici basati su parametri (es. codice ISO → ID tabella dominio).

---

> 🧠 **“`fn_get_default_by_param` standardizza il recupero di ID basati su parametri di configurazione, mantenendo la logica schema‑agnostica, tracciabile e con gestione errori uniforme.”**

{% include-markdown "signature-core.md" %}
