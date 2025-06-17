## 📘 Estensione PostgreSQL: `dblink`

L’estensione **`dblink`** di PostgreSQL permette l'esecuzione di query tra database PostgreSQL diversi o all’interno dello stesso server su database separati. È particolarmente utile per logging remoto, integrazioni di dati distribuiti e operazioni di sincronizzazione asincrone.

---

### 🎯 Scopo principale

* Eseguire query remote su altri database PostgreSQL.
* Effettuare operazioni di logging indipendenti dalla transazione corrente.
* Realizzare integrazioni e sincronizzazioni cross-database.

---

### ⚙️ Installazione

Per installare l'estensione, utilizzare:

```sql
CREATE EXTENSION IF NOT EXISTS dblink;
```

---

### 🛠️ Funzioni principali

* **`dblink_connect(text connname, text connstr)`**
  Stabilisce una connessione con nome (`connname`) usando una stringa di connessione.

* **`dblink_exec(text connname, text sql)`**
  Esegue un comando SQL remoto sulla connessione identificata.

* **`dblink_disconnect(text connname)`**
  Chiude la connessione identificata.

---

### 📋 Esempio d’uso in Zero ERP

Utilizzo comune per inserire un log di errore remoto isolato dalla transazione locale:

```plpgsql
PERFORM script.fn_ensure_logconn(); -- Assicura connessione

sql_text :=
  'INSERT INTO dbops.error_log(occurred_at, area, function_name, messaggio_errore_id, context, tx_id) VALUES (' ||
  'now(), ' || quote_literal(p_area) || ', ' || quote_literal(p_function_name) || ', ' ||
  coalesce(v_id::text,'NULL') || ', ' || quote_literal(v_context::text) || '::jsonb, ' ||
  quote_literal(md5(txid_current()::text)) || '::uuid' || ');';

PERFORM dblink_exec('logconn', sql_text);
```

Questo approccio permette al log dell'errore di essere salvato immediatamente e permanentemente anche se la transazione principale subisce un rollback.

---

### 🔒 Buone pratiche

* Gestire sempre le connessioni con nomi chiari e riutilizzabili.
* Assicurarsi che le stringhe di connessione siano configurate in modo sicuro tramite parametri personalizzati (GUC).
* Evitare query troppo complesse o massive via dblink per non compromettere le performance.

---

> 🧠 **“Utilizzare `dblink` consente una gestione robusta del logging distribuito e dell'integrazione di dati, garantendo operazioni isolate e indipendenti dalla transazione principale.”**