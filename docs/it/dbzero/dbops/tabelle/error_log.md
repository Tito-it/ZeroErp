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
| tx_id | uuid | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_error_log_messaggio_errore_id | messaggio_errore_id |
| PRIMARY KEY | error_log_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| error_log_pkey | `CREATE UNIQUE INDEX error_log_pkey ON dbops.error_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_assign_tx_id_error_log | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_assign_tx_id_error_log | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
---
{% include-markdown "signature-core.md" %}
