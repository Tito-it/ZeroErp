## 📘 Documentazione Concettuale – Function `script.fn_ensure_logconn()`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:   
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)     
> [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only)     

> Estensioni PostgreSQL:   
>
GUC `dblink.log_connection`
> Extension PostgreSQL `dblink`

La funzione **`script.fn_ensure_logconn()`** garantisce l’apertura di una connessione **dblink** permanente denominata **`logconn`**, utilizzando la stringa di connessione definita nella GUC `dblink.log_connection`. Se la connessione esiste già, l’eccezione `duplicate_object` viene catturata e ignorata.

---

### 🎯 Scopo Principale

* **Stabilire una connessione persistente** a un database remoto o a se stesso attraverso l’estensione `dblink`, evitando overhead di creazione/removal di connessioni multiple.
* **Supporto al logging remoto**: utilizzata da funzioni come `script.fn_log_error_only` per eseguire INSERT in un contesto transazionale separato.

---

* **`dblink_connect(connection_name, conninfo)`**: apre una connessione con nome `connection_name` sulla stringa `conninfo` (in formato URI o DSN).
* **GUC `dblink.log_connection`**: parametro di configurazione (custom) contenente la stringa di connessione.
* **Eccezione `duplicate_object`**: intercettata per evitare errori se `logconn` è già presente.

---

### Comportamenti e Side Effects

* **Persistenza della connessione**: rimane attiva fino alla fine della sessione o fino a `dblink_disconnect('logconn')`.
* **Idempotenza**: chiamate multiple non ricreano la connessione e non causano errori.
* **Assenza di rollback**: l’operazione di connessione non influisce sulle transazioni correnti.

---

### Esempi di Utilizzo

1. **Nel flusso di error handling**

   ```plpgsql
   -- Prima di loggare errori in remoto
   PERFORM script.fn_ensure_logconn();
   PERFORM dblink_exec('logconn', 'INSERT INTO dbops.error_log ...');
   ```

2. **Chiamata manuale**

   ```sql
   SELECT script.fn_ensure_logconn();
   ```

---

## Allegati / Best practice

* **Never-throw**: il logging non deve mai interrompere il flusso applicativo.
* **Isolamento**: usare canale `dblink` separato (`logconn`).
* **Context first**: includere nel log contesto utile (`tx_id`, chi/che-cosa/parametri).
* **Sicurezza**: ruoli dedicati ai log, `SECURITY DEFINER` solo quando serve, `search_path` esplicito.

---

### Vantaggi Operativi

* **Efficienza**: riduce la latenza di apertura connessioni ripetute.
* **Semplicità d’uso**: un’unica funzione per garantire la connessione.
* **Affidabilità**: ignora silenziosamente eccezioni di duplicato, evitando interruzioni.

---

> **“Un’utility leggera per gestire connessioni dblink persistenti, essenziale per pattern di logging remoto e task di integrazione tra database.”**