## 📘 Documentazione Concettuale – Funzione `script.fn_log_error_only`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) *(log + abort)*  
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn)  

Ultimo aggiornamento: **26/08/2025**



La funzione **`script.fn_log_error_only`** registra **solo** un messaggio in `dbops.error_log` **senza** interrompere l’esecuzione. È ideale per:

* Tracciare attività, eventi o warning che non devono bloccare il flusso applicativo.
* Loggare informazioni diagnostiche o transazionali di routine.

---

### 🎯 Scopo Principale

* **Logging “silenzioso”**: inserisce una riga in `dbops.error_log` con contesto ricco, ma **non** solleva eccezioni.
* **Separazione delle responsabilità**: differenzia chiaramente i casi di **solo tracciamento** da quelli di **error handling critico** (per cui usare `fn_log_and_raise_error`).

---

### Comportamento (contratto)

* **Never-throw:** eventuali errori del canale di log vengono **assorbiti** (il chiamante non viene interrotto).
* **Connessione separata:** il log avviene tramite **`dblink` dedicato** (`logconn`) per **isolare** il logging dalla transazione corrente.
* **Contesto ricco:** salva area, funzione, codice messaggio, `tx_id` e `context` JSONB.
* **Resilienza:**

  * se il codice non è in `config.messaggi_errore`, usa fallback (`'MESSAGGIO_NON_DEFINITO'`).
  * se `tx_id` non è passato, viene **recuperato/creato** (es. `dbops.fn_get_or_create_session_tx_id()`).
* **Idempotenza logica:** ogni chiamata genera una riga (nessun upsert necessario).

---

### Firma consigliata

```sql
-- Schema suggerito: script.*  
-- SECURITY DEFINER opzionale se serve accedere a risorse non concesse ai caller
CREATE OR REPLACE FUNCTION script.fn_log_error_only(
    p_area          text,
    p_function_name text,
    p_error_code    text,
    p_context       jsonb DEFAULT '{}'::jsonb,
    p_tx_id         uuid  DEFAULT NULL,
    VARIADIC p_valori text[]
) RETURNS void;
```

---

### Flusso interno (riassunto)

1. **Assicura connessione di log**: `PERFORM script.fn_ensure_logconn();`
2. **Tx id**: se `p_tx_id IS NULL` → `SELECT dbops.fn_get_or_create_session_tx_id();`
3. **Lookup messaggio**: legge `config.messaggi_errore` per lingua (GUC es. `myapp.user_language`). Fallback a `'MESSAGGIO_NON_DEFINITO'`.
4. **Formatting**: `format(v_msg, VARIADIC p_valori)` (se forniti).
5. **Insert via dblink**: `SELECT dblink_exec('logconn', $$INSERT ...$$);`
6. **Cattura errori**: qualsiasi eccezione viene intercettata e **non rilanciata**.

---

### Prerequisiti

* Estensione **`dblink`** installata nel DB dell’applicazione.
* GUC **`dblink.log_connection`** valorizzata con la conninfo del DB di logging (può coincidere con quello applicativo), es.:
  `postgresql://log_user:log_pwd@host:5432/appdb?sslmode=disable`
* Tabella **`dbops.error_log`** esistente.

---

### Sicurezza & Permessi

* Se si usa `dblink_connect_u`, richiede superuser o configurazioni ad hoc; preferibile `dblink_connect` con utente dedicato ai log.
* Valutare `SECURITY DEFINER` **solo se necessario** (es. log verso DB di servizio con credenziali dedicate). In tal caso impostare owner, `search_path` e GRANT con attenzione.
* Il **caller** necessita solo di `EXECUTE` sulla funzione; i permessi sulla tabella di log sono gestiti sul lato remoto via `dblink`.

---

### Esempio d’uso (PL/pgSQL)

```plpgsql
BEGIN
  -- ... logica applicativa ...
EXCEPTION WHEN OTHERS THEN
  PERFORM script.fn_log_error_only(
    p_area           => 'service',
    p_function_name  => 'sync_customer',
    p_error_code     => 'E_SYNC_WARN',
    p_context        => jsonb_build_object('customer_id', v_id, 'note', 'retry scheduled'),
    p_tx_id          => NULL,
    VARIADIC p_valori => ARRAY[coalesce(SQLERRM, 'n/a')]
  );
  -- prosegue senza RAISE
END;
```

---

### Troubleshooting

* **`dblink` non configurato** → la funzione continua “a vuoto” (non lancia). Verificare la GUC `dblink.log_connection` e l’operatività di `script.fn_ensure_logconn()`.
* **Messaggio non trovato** → verificare `config.messaggi_errore` o la lingua corrente; con fallback non si blocca.

---


### 💡 Vantaggi Operativi

* **Non blocca**: permette di tracciare eventi non critici senza interrompere transazioni o logica applicativa.
* **Contesto ricco**: i campi `messaggio_errore_id`, `context` e `tx_id` garantiscono alta tracciabilità.
* **Riutilizzabile**: può essere usata in trigger, stored procedure o funzioni PL/pgSQL per attività di auditing o monitoraggio.
* **Chiarezza**: distingue in modo esplicito il “solo logging” dal “log + abort” (`fn_log_and_raise_error`).

---

> 🧠 **“Usa `fn_log_error_only` per il logging passivo—per casi in cui vuoi solo registrare, mai bloccare.”**

