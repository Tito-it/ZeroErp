## 📘 Documentazione Concettuale – Funzione `script.fn_log_error_only`

> 👀 **Vedi anche**
>
> * [script.fn\_log\_and\_raise\_error](/dbzero/script/funzioni/fn_log_and_raise_error) *(log + abort)*

La funzione **`script.fn_log_error_only`** registra **solo** un messaggio in `dbops.error_log` **senza** interrompere l’esecuzione. È ideale per:

* Tracciare attività, eventi o warning che non devono bloccare il flusso applicativo.
* Loggare informazioni diagnostiche o transazionali di routine.

---

### 🎯 Scopo Principale

* **Logging “silenzioso”**: inserisce una riga in `dbops.error_log` con contesto ricco, ma **non** solleva eccezioni.
* **Separazione delle responsabilità**: differenzia chiaramente i casi di **solo tracciamento** da quelli di **error handling critico** (per cui usare `fn_log_and_raise_error`).

---

### 🔍 Parametri di Input

| Nome                | Tipo     | Descrizione                                                                                  |
| ------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `p_area`            | `TEXT`   | Area di applicazione (es. `'database'`, `'service'`, ecc.)                                   |
| `p_function_name`   | `TEXT`   | Nome della funzione o del contesto chiamante                                                 |
| `p_error_code`      | `TEXT`   | Codice di riferimento del messaggio in `config.messaggi_errore` (es. `'E_STORICO_MANCANTE'`) |
| `p_context`         | `JSONB`  | Oggetto JSON con informazioni di contesto (es. tabella, record, parametri)                   |
| `p_tx_id`           | `UUID`   | ID della transazione corrente (se `NULL`, viene generato automaticamente)                    |
| `VARIADIC p_valori` | `TEXT[]` | Valori da sostituire nei placeholder del messaggio (uso `format`)                            |

---

### ⚙️ Flusso di Esecuzione

1. **Recupero `tx_id`**: se `p_tx_id` è `NULL`, invoca `dbops.fn_get_or_create_session_tx_id()`.
2. **Lookup del messaggio**: cerca in `config.messaggi_errore` il record corrispondente a `p_error_code` e lingua (GUC `myapp.user_language`).

   * Se non trovato, usa il codice `'MESSAGGIO_NON_DEFINITO'`.
3. **Sostituzione placeholder**: applica `format(v_msg, VARIADIC p_valori)` se presenti.
4. **Insert su `dbops.error_log`**: costruisce dinamicamente l’`INSERT` con `dblink_exec` in connessione separata.
5. **Fine**: termina senza sollevare nulla, proseguendo il normale flusso PL/pgSQL.

---

### 💡 Vantaggi Operativi

* **Non blocca**: permette di tracciare eventi non critici senza interrompere transazioni o logica applicativa.
* **Contesto ricco**: i campi `messaggio_errore_id`, `context` e `tx_id` garantiscono alta tracciabilità.
* **Riutilizzabile**: può essere usata in trigger, stored procedure o funzioni PL/pgSQL per attività di auditing o monitoraggio.
* **Chiarezza**: distingue in modo esplicito il “solo logging” dal “log + abort” (`fn_log_and_raise_error`).

---

> 🧠 **“Usa `fn_log_error_only` per il logging passivo—per casi in cui vuoi solo registrare, mai bloccare.”**

---

