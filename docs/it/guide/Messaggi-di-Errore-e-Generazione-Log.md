# 📗 Guida Tecnica – Gestione dei Messaggi di Errore e Generazione Log in Zero ERP

> 📋 **Destinatari:** sviluppatori database, backend e devops

---

## 📌 Introduzione

Zero ERP adotta un modello unificato per la **centralizzazione**, il **logging** e la **gestione** dei messaggi di errore, basato su:

* **Tabella messaggi**: [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) – definisce template, cause e suggerimenti per ogni codice di errore.
* **Tabella log**: [dbops.error_log](/dbzero/dbops/tabelle/error_log) – archivia ogni occorrenza di errore con contesto e transazione.
* **Funzioni PL/pgSQL**:

  * [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio) per recuperare e formattare il testo del messaggio con internazionalizzazione e placeholder.
  * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) per eseguire il logging remoto e sollevare l’eccezione.

Questa guida illustra come utilizzare e estendere la struttura di errore, garantendo **consistenza**, **audit** e **facilità di manutenzione**.

---

## 🗂️ Definizione dei Messaggi di Errore

### 📚 Tabella `config.messaggi_errore`

> Dati di origine dei template di messaggio.

* **Path**: `config/messaggi_errore.md`
* **Scopo Principale**: mantenere un catalogo multilingua di messaggi, cause e suggerimenti.
* **Campi chiave**:

  * `codice` (TEXT, PK): identificativo del messaggio.
  * `lingua` (TEXT): lingua del template (`it`, `en`, …).
  * `messaggio` (TEXT): testo con placeholder `%s`.
  * `causa` / `soluzione` (TEXT): dettagli per `DETAIL` e `HINT` dell’eccezione.

> Consulta la documentazione dettagliata: [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)

---

## 📑 Archiviazione degli Errori

### 📚 Tabella `dbops.error_log`

> Registro immutabile di tutte le occorrenze di errore.

* **Path**: `dbops/error_log.md`
* **Scopo Principale**: tracciare (timestamp, area, funzione, contesto JSONB) ogni errore prima dell’eccezione.
* **Campi chiave**:

  * `occurred_at` (TIMESTAMPTZ): istante di logging.
  * `area` / `function_name`: ambito e origine.
  * `messaggio_errore_id`: FK a `config.messaggi_errore.id`.
  * `context` (JSONB): payload di variabili/circostanze.
  * `tx_id` (UUID): transazione correlata.

> Consulta la documentazione dettagliata: [dbops.error_log](/dbzero/dbops/tabelle/error_log)

---

## ⚙️ Funzioni di Supporto

### 📘 `script.fn_get_messaggio`

> Recupera e formatta un messaggio dal catalogo

* **Path**: `script/fn_get_messaggio.md`
* **Scopo**: internazionalizzare e sostituire placeholder `%s` nel testo.
* **Link**: [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)

### 📘 `script.fn_log_and_raise_error`

> Esegue il logging remoto e solleva l’eccezione

* **Path**: `script/fn_log_and_raise_error.md`
* **Scopo**: unificare logging via `dblink_exec` e `RAISE EXCEPTION` con `DETAIL` e `HINT`.
* **Link**: [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 📘 `script.fn_log_error_only`

> Esegue il logging remoto ma non solleva l’eccezione

* **Path**: `script/fn_log_error_only.md`
* **Scopo**: unificare logging via `dblink_exec` .
* **Link**: [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only)

> **Nota operativa (PG18)**  
> Per garantire logging **persistente** anche in caso di rollback (out‑of‑transaction),  
> `script.fn_log_error_only` **deve essere `SECURITY DEFINER`** ed **owner superuser** (es. `postgres`).  
> La connessione `dblink` va configurata tramite **`pg_service.conf` + `.pgpass`** sul server PostgreSQL,
> con `myapp.dblink_log_connection = 'service=<nome>'`.  
> In caso contrario si ottiene errore `2F003` (password/GSSAPI richiesti).

---

## ✅ Setup operativo dblink (log persistente)

### 1) Ruolo di logging con privilegi minimi

Eseguire da utente admin (es. `postgres`) nel DB applicativo:

```sql
CREATE EXTENSION IF NOT EXISTS dblink;

CREATE ROLE zeroerp_log LOGIN PASSWORD 'PASSWORD_FORTE';
GRANT USAGE ON SCHEMA dbops TO zeroerp_log;
GRANT INSERT ON TABLE dbops.error_log TO zeroerp_log;
GRANT USAGE, SELECT ON SEQUENCE dbops.error_log_id_seq TO zeroerp_log;
```

### 2) Configurare `pg_service.conf` (server PostgreSQL)

I file devono essere creati **sul server DB**, nella HOME dell’utente OS `postgres`
(tipicamente `/var/lib/postgresql`).

`/var/lib/postgresql/.pg_service.conf`:

```
[zeroerp_log]
host=127.0.0.1
port=5432
dbname=zeroerp
user=zeroerp_log
```

### 3) Configurare `.pgpass` (server PostgreSQL)

`/var/lib/postgresql/.pgpass`:

```
127.0.0.1:5432:zeroerp:zeroerp_log:PASSWORD_FORTE
```

Permessi obbligatori:

```bash
chown postgres:postgres /var/lib/postgresql/.pg_service.conf /var/lib/postgresql/.pgpass
chmod 600 /var/lib/postgresql/.pg_service.conf /var/lib/postgresql/.pgpass
```

Se il servizio PostgreSQL non legge la HOME, forzare i path con systemd:

```
[Service]
Environment=PGSERVICEFILE=/var/lib/postgresql/.pg_service.conf
Environment=PGPASSFILE=/var/lib/postgresql/.pgpass
```

e riavviare `postgresql@<versione>-main`.

### 4) Impostare la GUC per i ruoli applicativi

Eseguire da admin:

```sql
ALTER ROLE titodb     IN DATABASE zeroerp SET myapp.dblink_log_connection = 'service=zeroerp_log';
ALTER ROLE zeroerp_app IN DATABASE zeroerp SET myapp.dblink_log_connection = 'service=zeroerp_log';
```

---

## 🔧 Verifiche e test

### Test corretto (via funzione SECURITY DEFINER)

```sql
SELECT script.fn_log_error_only(
  'test',
  'diag_log_only',
  'E_GENERICO',
  jsonb_build_object('probe','manual_test','ts',clock_timestamp()),
  NULL::uuid
);

SELECT *
FROM dbops.error_log
ORDER BY occurred_at DESC
LIMIT 5;
```

### Errori tipici

* **`2F003` (password/GSSAPI richiesti)**  
  La funzione non è `SECURITY DEFINER` o non è owner superuser; oppure `pg_service.conf/.pgpass` non sono visibili al processo postgres.
* **Log non presente ma nessun errore**  
  Verificare `myapp.dblink_log_connection`, `pg_service.conf/.pgpass`, e permessi del ruolo `zeroerp_log`.

---

## 🔐 Hardening owner funzioni (Liquibase)

Per garantire owner `postgres` alle funzioni sensibili (inclusa `script.fn_log_error_only`),
si usa il changeSet:

`migrations_v2/90_end/20251123-12-sec-functions-owner-hardening-mctit.yaml`

Questo esegue `dbops.fn_sync_functions_owner()` che legge `dbops.sec_functions_owner`.
La funzione `script.fn_log_error_only` è registrata nella tabella e viene riallineata a `postgres`.

**Esecuzione consigliata (admin):**

```bash
scripts/liquibase5.sh update --contexts=provision --username=postgres --password=***
```

---

## 🔄 Flusso di Gestione degli Errori

1. **Validazione/Check** in trigger o procedure PL/pgSQL.
2. **Invocazione** di `script.fn_log_and_raise_error(`

   * parametri: `p_area`, `p_function_name`, `p_error_code`, `p_context`, (varargs)
   * il logging avviene su `dbops.error_log` in una connessione dedicata.
3. **Recupero** del testo con `script.fn_get_messaggio` (interno a `fn_log_and_raise_error`).
4. **Raise** dell’eccezione con `RAISE EXCEPTION`, includendo `DETAIL` e `HINT`.

L’applicazione riceverà l’errore formattato, mentre il database manterrà un audit completo.

---

## 🧭 Routing Errori Applicativi (pipeline/domini)

Per i processi applicativi (es. pipeline fatturazione) il log tecnico generale su
`dbops.error_log` **non sostituisce** i log di dominio.  
Si applica quindi un routing esplicito:

* `scope = LOTTO` -> log su `vendite.fatturazione_lotti_log`
* `scope = FATTURA` -> log su `vendite.fatture_log`
* in entrambi i casi resta attivo anche il log tecnico standard (`dbops.error_log`)

### Contratto minimo consigliato (backend)

* `scope`: `LOTTO` | `FATTURA`
* `severity`: `I` | `W` | `C`
* `code`: codice errore stabile
* `message`: messaggio sintetico
* `detail`: dettaglio tecnico
* `lotto_id`: obbligatorio nei processi pipeline
* `fattura_id`: obbligatorio se `scope = FATTURA`
* `context/meta`: JSON con task, step, funzione, parametri

### Esempi pratici (stato attuale vendite)

* Avanzamento step pipeline -> `vendite.fn_log_pipeline_fase(...)` su `fatturazione_lotti_log`.
* Esito severità lotto (C > W > I) -> `vendite.fn_log_lotto_esito_fatture(...)`.
* Errori documento specifici (es. reset fondi bloccato da contabilizzazione) -> `vendite.fatture_log`.
* Errori SQL/raise (`script.fn_log_and_raise_error`) -> `dbops.error_log`.

Questa regola è riusabile per altri domini (es. `ATTIVITA_FATTURABILI`, `PRATICHE`) mantenendo lo stesso contratto (`scope`, `severity`, `code`, `context`) e cambiando solo i target log di dominio.

---

## 💡 Best Practices

* **Centralizzare tutti i messaggi** in `config.messaggi_errore`, senza hard‑coding di testi.
* **Usare codici coerenti** e documentati (es. `ERR_TIMEOUT`, `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`).
* **Popolare il `context`** con dati rilevanti (ID, payload, parametri) per facilitare il debug.
* **Sfruttare la multilingua** definendo template in più lingue e usando il GUC `myapp.user_language`.
* **Monitoraggio**: creare viste o dashboard su `dbops.error_log` per alert e metriche di errore.
* **Evoluzione dello schema**: il JSONB `context` e il modello di log separato preservano la flessibilità nelle colonne future.

---

> 🧠 **“Un approccio unificato al logging e all’exception handling in Zero ERP garantisce qualità, tracciabilità e facilità di manutenzione: dai template in tabella alle connessioni dblink, fino alle eccezioni multilingua.”**

---

{% include-markdown "signature-core.md" %}
