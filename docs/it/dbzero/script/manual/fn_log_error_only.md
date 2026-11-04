## 📘 Documentazione Concettuale – Funzione `script.fn_log_error_only`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) *(log + abort)*
> * [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa) — la regola unica: se il canale è acceso, e con quale stringa
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — la connessione persistente `logconn`, il secondo tentativo



La funzione **`script.fn_log_error_only`** registra **solo** un messaggio in `dbops.error_log` **senza** interrompere l’esecuzione. È ideale per:

* Tracciare attività, eventi o warning che non devono bloccare il flusso applicativo.
* Loggare informazioni diagnostiche o transazionali di routine.

---
### 🎯 Scopo Principale
(latest review 23-11-25)
* **Logging “silenzioso”**: inserisce una riga in `dbops.error_log` con contesto ricco, ma **non** solleva eccezioni.
* **Separazione delle responsabilità**: differenzia chiaramente i casi di **solo tracciamento** da quelli di **error handling critico** (per cui usare `fn_log_and_raise_error`).

---

### Comportamento (contratto)

* **Never-throw:** eventuali errori del canale di log vengono **assorbiti** (il chiamante non viene interrotto).
* **Canale acceso o spento:** lo dice `script.fn_canale_log_stringa`. Con il canale spento (`myapp.log_with_dblink = off`) o non configurato (nessuna stringa di connessione) la funzione emette un `WARNING` e **non registra niente**.
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

1. **Tx id**: se `p_tx_id IS NULL` → `SELECT dbops.fn_get_or_create_session_tx_id();` (con il canale spento è la sentinella `script.uuid_nil()`).
2. **Lookup messaggio**: legge `config.messaggi_errore` per lingua (GUC es. `myapp.user_language`). Fallback a `'MESSAGGIO_NON_DEFINITO'`.
3. **Formatting**: `format(v_msg, VARIADIC p_valori)` (se forniti).
4. **Il canale**: `script.fn_canale_log_stringa()`. Se restituisce `NULL` (spento o non configurato): `WARNING` e uscita, nessuna scrittura.
5. **Insert via dblink, primo tentativo**: `dblink_exec(<stringa del canale>, $$INSERT ...$$)`.
6. **Secondo tentativo**: se il primo fallisce, `script.fn_ensure_logconn()` apre o ritrova `logconn` e l'INSERT si riprova lì.
7. **Cattura errori**: qualsiasi eccezione viene intercettata e **non rilanciata**; se nessun tentativo riesce resta un `WARNING`.

---

### Prerequisiti

* Estensione **`dblink`** installata nel DB dell’applicazione.
* Una stringa di connessione per il canale: **`myapp.logconn`** se valorizzato, altrimenti **`myapp.dblink_log_connection`** (in Zero ERP `'service=zeroerp_log'`, impostata per ruolo dal provisioning del canale). Il DB di logging può coincidere con quello applicativo.
* L'interruttore **`myapp.log_with_dblink`** non a `off` (assente vale acceso). La regola completa è in [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa).
* Tabella **`dbops.error_log`** esistente.

---

### Sicurezza & Permessi

* Per **logging out-of-transaction** via `dblink` senza password in GUC, **la funzione deve essere `SECURITY DEFINER`** e **owner superuser** (es. `postgres`).
  In caso contrario, il caller non superuser riceve `2F003` (password/GSSAPI richiesti).
* Usare un utente dedicato ai log (es. `zeroerp_log`) con privilegi **minimi** su `dbops.error_log`.
* Configurare **`pg_service.conf` + `.pgpass`** sul server PostgreSQL (utente OS `postgres`) per il service usato da `myapp.dblink_log_connection`.
* In modalità `SECURITY DEFINER`, mantenere `search_path` ristretto e garantire `GRANT EXECUTE` solo ai ruoli necessari.
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

* **`dblink` non configurato o canale spento** → la funzione continua “a vuoto” (non lancia, emette un `WARNING`). Verificare `myapp.log_with_dblink` (non deve valere `off`), la stringa `myapp.logconn` / `myapp.dblink_log_connection` e l’operatività di `script.fn_ensure_logconn()`.
* **Errore `2F003` (password/GSSAPI richiesti)** → la funzione non è `SECURITY DEFINER` o non è owner superuser; verificare anche `pg_service.conf/.pgpass`.
* **Messaggio non trovato** → verificare `config.messaggi_errore` o la lingua corrente; con fallback non si blocca.

---


### Vantaggi Operativi

* **Non blocca**: permette di tracciare eventi non critici senza interrompere transazioni o logica applicativa.
* **Contesto ricco**: i campi `messaggio_errore_id`, `context` e `tx_id` garantiscono alta tracciabilità.
* **Riutilizzabile**: può essere usata in trigger, stored procedure o funzioni PL/pgSQL per attività di auditing o monitoraggio.
* **Chiarezza**: distingue in modo esplicito il “solo logging” dal “log + abort” (`fn_log_and_raise_error`).

---

> **“Usa `fn_log_error_only` per il logging passivo—per casi in cui vuoi solo registrare, mai bloccare.”**

---

### Test

* `db/pgtap/script/test-canale-log-v1.sql` — test 11: con un canale irraggiungibile la funzione non
  solleva. Test 14: con `myapp.log_with_dblink = off` e un canale che funziona non scrive in
  `dbops.error_log` (si salta dove il canale non c'è). Test 16: non legge da sé i parametri del
  canale (presidio sul testo).

---

### Note di migrazione

* 2026-11-04 — il canale lo dice `script.fn_canale_log_stringa` (D26 di `brief-db-revisione-dbops`):
  prima la funzione ignorava l'interruttore `myapp.log_with_dblink`, e con `off` e la stringa
  impostata registrava lo stesso fuori transazione; la precedenza di `myapp.logconn`, scritta qui a
  mano, sta ora nel building block. Firma e variabili prendono i tipi dalle colonne (`%TYPE`); la
  firma risolta non cambia.

---

{% include-markdown "signature-core.md" %}
