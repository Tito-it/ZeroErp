{% include-markdown "it/dbzero/dbops/manual/error_log.md" %}
# 📚 Tabella `error_log`

> 📝 **Descrizione**
>
> Log centralizzato di errori, con informazioni su area, funzione, colleggata a messaggi_errore e contesto

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
| cleanup_at | timestamp with time zone | YES |  |

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
| ix_error_log_area_occurred_at | `CREATE INDEX ix_error_log_area_occurred_at ON dbops.error_log USING btree (area, occurred_at)` |
| ix_error_log_cleanup_at | `CREATE INDEX ix_error_log_cleanup_at ON dbops.error_log USING btree (cleanup_at)` |
| ix_error_log_function_name_occurred_at | `CREATE INDEX ix_error_log_function_name_occurred_at ON dbops.error_log USING btree (function_name text_pattern_ops, occurred_at)` |
| ix_error_log_occurred_at | `CREATE INDEX ix_error_log_occurred_at ON dbops.error_log USING btree (occurred_at)` |
| ix_error_log_tx_id | `CREATE INDEX ix_error_log_tx_id ON dbops.error_log USING btree (tx_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_error_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_error_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
