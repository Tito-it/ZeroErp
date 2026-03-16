## Estensione PostgreSQL: `dblink`

> **Vedi anche**
>
> Approfondimenti correlati:
> - [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn)
> - [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id)

L'estensione **`dblink`** consente l'esecuzione di query tra database PostgreSQL diversi o sullo stesso server ma su database separati. In Zero ERP e' utilizzata principalmente per:

* Logging remoto indipendente dalla transazione corrente
* Operazioni tecniche asincrone
* Sincronizzazioni e integrazioni *cross-database*

---

## Sezione critica — Configurazione necessaria prima dell'utilizzo

> **FONDAMENTALE**
> Prima di utilizzare `dblink`, e' necessario configurare correttamente i parametri di connessione.
> Questa operazione **deve essere eseguita come `postgres`** (utente superuser) e puo' essere necessaria *dopo ogni clonazione o restore del database*.

### 1. Evitare password in chiaro

Utilizzare **pg_service.conf** anziche' inserire direttamente `password=` nei parametri.

Percorso consigliato (utente `postgres`):

```
/var/lib/postgresql/.pg_service.conf
```

Esempio contenuto:

```ini
[zeroerp_log]
dbname=zeroerp
host=localhost
user=titodb
password=******
```

Permessi suggeriti:

```bash
sudo chown postgres:postgres /var/lib/postgresql/.pg_service.conf
sudo chmod 600 /var/lib/postgresql/.pg_service.conf
```

---

### 2. Impostare il parametro di connessione (GUC)

Eseguire come utente `postgres`:

```sql
ALTER DATABASE zeroerp
  SET myapp.dblink_log_connection = 'service=zeroerp_log';
```

Verifica caricamento parametro:

```sql
SHOW myapp.dblink_log_connection;
-- Atteso: "service=zeroerp_log"
```

---

### 3. Test funzionale tramite funzione

Dopo aver impostato la configurazione, verificare:

```sql
SELECT script.fn_ensure_logconn();

SELECT dbops.fn_get_or_create_session_tx_id();
```

**Nota:**
Per funzione fn_get_or_create_session_tx_id risultato atteso la generazione di un UUID, verificare su messaggi che non ci siano segnalazioni. Eseguire la function su una nuova sessione SQL (su pgAdmin) in modo da essere certi che non ci siano precedenti attivita'.

---

## Procedura completa (nuovo ambiente / restore DB)

| Step | Azione                                      | Eseguito come      |
| ---- | ------------------------------------------- | ------------------ |
| 1    | Abilitare estensione dblink                 | postgres           |
| 2    | Creare utente tecnico (es. `titodb`)        | postgres           |
| 3    | Configurare `.pg_service.conf`              | root/postgres      |
| 4    | Impostare GUC `myapp.dblink_log_connection` | postgres           |
| 5    | Verifica con `fn_ensure_logconn()`          | utente tecnico/app |

---

## Installazione estensione

```sql
CREATE EXTENSION IF NOT EXISTS dblink;
```

---

## Funzioni principali

| Funzione                                      | Descrizione              |
| --------------------------------------------- | ------------------------ |
| `dblink_connect(text connname, text connstr)` | Apre connessione remota  |
| `dblink_exec(text connname, text sql)`        | Esegue SQL sul DB remoto |
| `dblink_disconnect(text connname)`            | Chiude la connessione    |

---

## Esempio d'uso in Zero ERP

```plpgsql
PERFORM script.fn_ensure_logconn(); -- Assicura connessione log

sql_text :=
  'INSERT INTO dbops.error_log(occurred_at, area, function_name, messaggio_errore_id, context, tx_id) VALUES (' ||
  'now(), ' || quote_literal(p_area) || ', ' || quote_literal(p_function_name) || ', ' ||
  coalesce(v_id::text,'NULL') || ', ' || quote_literal(v_context::text) || '::jsonb, ' ||
  quote_literal(md5(txid_current()::text)) || '::uuid' || ');';

PERFORM dblink_exec('logconn', sql_text);
```

Questo approccio garantisce che il log venga salvato **indipendentemente dalla transazione principale**, anche in caso di rollback.

---

## Buone pratiche Zero ERP

* Utilizzare **utente tecnico dedicato** (es. `titodb`)
* Evitare password in chiaro nei parametri GUC
* Usare connessioni preconfigurate (`service=...`)
* Utilizzare `script.fn_ensure_logconn()` come controllo iniziale
* Dopo restore/clonazione → ricreare `.pg_service.conf` e reimpostare parametro

---

> *"L'utilizzo corretto di `dblink` garantisce logging distribuito affidabile e integrazione tecnica sicura, mantenendo l'operativita' isolata dalla transazione principale."*

---

{% include-markdown "signature-core.md" %}
