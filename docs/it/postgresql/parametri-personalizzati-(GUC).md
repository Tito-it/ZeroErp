## 📘 Parametri Personalizzati (GUC) in PostgreSQL

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [config.parameters](/dbzero/config/tabelle/parameters)   
> - [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)   
>
> Approfondimento funzioni:
> - [script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)   
>
> All’interno del documento viene spiegata la differenza tra parametri GUC e parametri tabellari.

I **Parametri Personalizzati (GUC – Grand Unified Configuration)** di PostgreSQL consentono di definire variabili di configurazione custom, accessibili da funzioni, trigger e dalla sessione SQL. Sono ideali per configurazioni DB‑centriche, centralizzate e versionabili tramite `postgresql.conf` o comandi SQL.

---

### 🎯 Scopo Principale

* Centralizzare configurazioni applicative specifiche direttamente nel database.
* Modificare dinamicamente parametri senza toccare il codice applicativo.
* Rendere disponibili “feature flags”, stringhe di connessione, lingua, ecc., in modo uniforme.

---

### 🛠️ Definizione e Utilizzo

Si definiscono in `postgresql.conf` o con:

```sql
ALTER DATABASE zeroerp SET myapp.user_language = 'it';
ALTER ROLE app_user   SET myapp.bypass_tx_id_check = 'on';
```

Si leggono in PL/pgSQL o SQL con:

```sql
SELECT current_setting('myapp.user_language', TRUE);
```

e si possono modificare in sessione:

```sql
SET myapp.user_language = 'en';
```

---

### ⚖️ Tipologie di GUC

| Tipo di GUC           | Prefisso | Stabilità              | Scope                                   |
| --------------------- | -------- | ---------------------- | --------------------------------------- |
| **Di sistema**        | `myapp.` | Persistente (conf/db)  | Cluster, Database, Role, Session        |
| **Di infrastruttura** | `dbops.` | Temporanee (GUC local) | Solo within-session (es. `dbops.tx_id`) |

* **GUC di sistema** (`myapp.*`):
  Parametri applicativi centrali (es. lingua, dblink, feature-flag). Definiti in `postgresql.conf`, `ALTER SYSTEM`, `ALTER DATABASE` o `ALTER ROLE`.
* **GUC temporanee/infrastrutturali** (`<schema>.<name>`):
  Usate da trigger e funzioni per passare variabili di sessione (es. `dbops.tx_id`). Vengono settate con `set_config(…, is_local := TRUE)` e reset al commit/rollback.

---

### 📋 Esempi di GUC in Zero ERP

* **`myapp.dblink_log_connection`**
  Stringa di connessione per `dblink`, usata per log remoti fuori dalla transazione corrente. **Importante per** [`Dblink`](/postgresql/dblink.md) fare riferimento alla apposita documentazione.

  ```conf
  myapp.dblink_log_connection = 'host=localhost port=5432 dbname=Zero user=xx password=xx'
  ```
* **`myapp.user_language`**
  Lingua di default per le funzioni applicative.

  ```conf
  myapp.user_language = 'it'
  ```
* **`myapp.bypass_tx_id_check`**
  Flag booleano per abilitare/disabilitare il controllo obbligatorio di `tx_id` nel trigger.

  ```conf
  myapp.bypass_tx_id_check = off
  ```
* **`dbops.tx_id`** *(temporanea)*
  UUID di sessione che identifica le operazioni della stessa transazione. Viene settato da trigger PL/pgSQL e reset al commit/rollback.

---

### 🤝 Differenza GUC vs Parametri Tabellari

| Caratteristica       | GUC (`myapp.*`, `dbops.*`)                        | Tabelle (`config.parameters` + overrides)                  |
| -------------------- | ------------------------------------------------- | ---------------------------------------------------------- |
| **Scope**            | Cluster/DB/Role/Session                           | Record-level (tenant, utente, funzione, sessione)          |
| **Versioning/Audit** | No (solo DDL o conf file)                         | Sì (Liquibase, trigger di audit, date_insert, ecc.)       |
| **Dinamico**         | Sì (SET/ALTER in sessione)                        | Sì (modificabile in runtime con query)                     |
| **Use case**         | Configurazioni DB-centriche (lingua, connessioni) | Configurazioni business-centriche (feature-flag, timeouts) |

---

### 🗂️ Documentazione e Allegati

* **Documento Principale** (questo): introduce GUC e best practice.
* **Elenco GUC Definite**: crea un file separato (`guc_reference.md` o `.xlsx`) contenente tabella con:

  * `nome parametro`
  * `default`
  * `scope` (cluster/db/role/session)
  * `descrizione`
  * `schema/funzione che lo usa`

> **Suggerimento**: per estrarre le GUC già definite in conf usa:
>
> ```sql
> SELECT name, setting
>   FROM pg_settings
>  WHERE name LIKE 'myapp.%' OR name LIKE 'dbops.%'
>  ORDER BY name;
> ```

---

### 🗂️ Comandi Utili
> ```sql
>
> -- Mostra la path di postgresql.conf   
>SHOW config_file;    
>  -- Mostra i parametri GUC definiti in :    
>SHOW myapp.user_language;     -- (Show nome Guc)
>
> ```

---

### 🔒 Best Practices

1. Usare **prefissi chiari** (`myapp.` per sistema, `<schema>.` per variabili di sessione).
2. Documentare ogni parametro in `postgresql.conf` e in `guc_reference.md`.
3. Gestire valori sensibili con Vault, non in GUC.
4. Caricare in cache in applicazione e rinfrescare periodicamente.

> 🧠 **“Standardizza i prefissi, separa configurazioni di sistema da quelle transazionali e mantieni sempre un elenco aggiornato da allegare ai tuoi rilasci.”**

---


---
{% include-markdown "signature-core.md" %}
