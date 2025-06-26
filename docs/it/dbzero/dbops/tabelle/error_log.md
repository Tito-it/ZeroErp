{% include-markdown "it/dbzero/dbops/manual/error_log.md" %}
# 📚 Tabella `error_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('dbops.error_log_id_seq'::regclass) |
| occurred_at | timestamp with time zone | NO | now() |
| area | text | NO |  |
| function_name | text | NO |  |
| messaggio_errore_id | bigint | NO |  |
| context | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | NO | (md5((txid_current())::text))::uuid |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_error_log_messaggio_errore_id | messaggio_errore_id |
| PRIMARY KEY | error_log_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| error_log_pkey | `CREATE UNIQUE INDEX error_log_pkey ON dbops.error_log USING btree (id)` |
| ix_dbops_error_log_messaggio_errore_id | `CREATE INDEX ix_dbops_error_log_messaggio_errore_id ON dbops.error_log USING btree (messaggio_errore_id)` |