## Parametri Personalizzati (GUC) in PostgreSQL

>
> (latest review 02-02-26)
>
> **Vedi anche**
>
> * [GUC definite in ZeroErp](/postgresql/guc_reference.md)
>
> Approfondimento Tabelle:
> - [config.parameters](/dbzero/config/tabelle/parameters)
> - [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
>
> Approfondimento funzioni:
> - [script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)
>
> All'interno del documento viene spiegata la differenza tra parametri GUC e parametri tabellari.

I **Parametri Personalizzati (GUC — Grand Unified Configuration)** di PostgreSQL consentono di definire variabili di configurazione custom, accessibili da funzioni, trigger e dalla sessione SQL. Sono ideali per configurazioni DB-centriche, centralizzate e versionabili tramite `postgresql.conf` o comandi SQL.

---

### Scopo Principale

* Centralizzare configurazioni applicative specifiche direttamente nel database.
* Modificare dinamicamente parametri senza toccare il codice applicativo.
* Rendere disponibili "feature flags", stringhe di connessione, lingua, ecc., in modo uniforme.

---

### Definizione e Utilizzo

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

### Tipologie di GUC

| Tipo di GUC           | Prefisso | Stabilita'             | Ambito                                  |
| --------------------- | -------- | ---------------------- | --------------------------------------- |
| **Di sistema**        | `myapp.` | Persistente (conf/db)  | Cluster, Database, Role, Session        |
| **Di infrastruttura** | `dbops.` | Temporanee (GUC local) | Solo within-session (es. `dbops.tx_id`) |

* **GUC di sistema** (`myapp.*`):
  Parametri applicativi centrali (es. lingua, dblink, feature-flag). Definiti in `postgresql.conf`, `ALTER SYSTEM`, `ALTER DATABASE` o `ALTER ROLE`.
* **GUC temporanee/infrastrutturali** (`<schema>.<name>`):
  Usate da trigger e funzioni per passare variabili di sessione (es. `dbops.tx_id`). Vengono settate con `set_config(..., is_local := TRUE)` e reset al commit/rollback.

---

### Esempi di GUC in Zero ERP

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

### GUC di sessione `app.*` (contesto identità multi-face-auth)

Il prefisso **`app.`** è riservato alle GUC **session-scoped** popolate dal
middleware `JwtAuditAuthentication` al momento dell'autenticazione HTTP e
resettate in `process_response`. Descrivono il **contesto identità** della
richiesta corrente e sono lette da:

* funzioni resolver (`fn_resolve_*`, `fn_check_*`, `fn_scope_*`),
* policy RLS (§4.9 WIP multi-face-auth),
* trigger di audit/log che collegano operazioni DB → identità utente.

Tutte sono impostate via `set_config('app.<nome>', <valore>, is_local := false)`
a livello di sessione dalla connessione del pool (reset a fine request).

#### Set base (pre-esistente)

* **`app.jwt_user`** — username stringa dell'utente Django autenticato.
* **`app.current_user_id`** — `auth_user.id` come stringa.

#### Set multi-face-auth (§4.7 WIP, introdotti 2026-04-19)

Tre GUC aggiuntive descrivono la **veste** con cui l'utente accede in questa
sessione (operatore interno vs cliente portale vs fornitore vs shop vs api
client), usate dalle policy di scope / RLS per filtrare i dati in modo
coerente col ruolo applicativo:

* **`app.current_identita_id`** — `anagrafiche.identita_digitali.id` della
  veste attiva per questa sessione. Lettura tipica: `NULLIF(current_setting('app.current_identita_id', true), '')::bigint`.
* **`app.ruolo_applicativo`** — valore dell'enum `config.ruolo_applicativo`
  dell'identità corrente. Usato dalle policy che vincolano l'accesso per
  dimensione "chi sei" (es. i `CLIENTE_PORTALE` non vedono l'area acquisti).
* **`app.soggetto_ruolo_id`** — `anagrafiche.soggetti_ruoli.id` dell'identità
  corrente. Usato da policy **BA_OWNERSHIP** / **FORNITORE_OWNERSHIP** per
  mappare l'utente al soggetto anagrafico proprietario dei dati.

#### Helper `script.fn_current_identita_context()`

Per leggere tutte e tre le GUC in un colpo solo e ottenere un record
tipato, usare la funzione di convenienza
[`script.fn_current_identita_context`](/dbzero/script/funzioni/fn_current_identita_context):

```sql
SELECT * FROM script.fn_current_identita_context();
--  current_identita_id | ruolo_applicativo | soggetto_ruolo_id
-- ---------------------+-------------------+-------------------
--                   42 | OPERATORE         |               123
```

La funzione fa il parsing dei tre GUC (fail-soft: restituisce `NULL` per i
campi non impostati) e applica i cast ai tipi corretti.

#### Invariante "tutto o niente"

Il middleware **deve** popolare tutti e tre i GUC contemporaneamente (oppure
nessuno, per i percorsi non autenticati): dati parziali producono stati
incoerenti nelle policy RLS. Se una sola delle tre è `NULL`, le policy
applicate via `fn_scope_*` falliscono in modo **fail-closed**.

---

### Differenza GUC vs Parametri Tabellari

| Caratteristica       | GUC (`myapp.*`, `dbops.*`)                        | Tabelle (`config.parameters` + overrides)                  |
| -------------------- | ------------------------------------------------- | ---------------------------------------------------------- |
| **Ambito**           | Cluster/DB/Role/Session                           | Record-level (tenant, utente, funzione, sessione)          |
| **Versioning/Audit** | No (solo DDL o conf file)                         | Si' (Liquibase, trigger di audit, data_insert, ecc.)       |
| **Dinamico**         | Si' (SET/ALTER in sessione)                       | Si' (modificabile in runtime con query)                    |
| **Use case**         | Configurazioni DB-centriche (lingua, connessioni) | Configurazioni business-centriche (feature-flag, timeouts) |

---

### Documentazione e Allegati

* **Documento Principale** (questo): introduce GUC e best practice.
* **Elenco GUC Definite**: vedi il file [`guc_reference.md`](/postgresql/guc_reference) con tabella di riferimento contenente:

  * `nome parametro`
  * `default`
  * `ambito` (cluster/db/role/session)
  * `descrizione`
  * `schema/funzione che lo usa`

> **Suggerimento**: per estrarre le GUC gia' definite in conf usa:
>
> ```sql
> SELECT name, setting
>   FROM pg_settings
>  WHERE name LIKE 'myapp.%' OR name LIKE 'dbops.%'
>  ORDER BY name;
> ```

---

### Comandi Utili

```sql
-- Mostra la path di postgresql.conf
SHOW config_file;
-- Mostra i parametri GUC definiti:
SHOW myapp.user_language;     -- (Show nome Guc)
```

---

### Best Practices

1. Usare **prefissi chiari** (`myapp.` per sistema, `<schema>.` per variabili di sessione).
2. Documentare ogni parametro in `postgresql.conf` e in `guc_reference.md`.
3. Gestire valori sensibili con Vault, non in GUC.
4. Caricare in cache in applicazione e rinfrescare periodicamente.

> **"Standardizza i prefissi, separa configurazioni di sistema da quelle transazionali e mantieni sempre un elenco aggiornato da allegare ai tuoi rilasci."**

---

---
{% include-markdown "signature-core.md" %}
