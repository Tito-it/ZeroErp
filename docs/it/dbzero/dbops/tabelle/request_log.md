{% include-markdown "it/dbzero/dbops/manual/request_log.md" %}
# 📚 Tabella `request_log`

> 📝 **Descrizione**
>
> Log request API: registra utente, endpoint, metodo, status e durata per ogni request /api/*.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | YES |  |
| username | text | YES |  |
| request_id | uuid | YES |  |
| method | text | NO |  |
| path | text | NO |  |
| query_string | text | YES |  |
| status_code | smallint | YES |  |
| duration_ms | integer | YES |  |
| ip_address | inet | YES |  |
| user_agent | text | YES |  |
| error_code | text | YES |  |
| idempotency_key | text | YES |  |
| cleanup_at | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| emittente_attivo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_request_log_method |  |
| PRIMARY KEY | pk_request_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_request_log_auth_user_id | `CREATE INDEX ix_request_log_auth_user_id ON dbops.request_log USING btree (auth_user_id)` |
| ix_request_log_cleanup_at | `CREATE INDEX ix_request_log_cleanup_at ON dbops.request_log USING btree (cleanup_at)` |
| ix_request_log_data_insert | `CREATE INDEX ix_request_log_data_insert ON dbops.request_log USING btree (data_insert DESC)` |
| ix_request_log_path | `CREATE INDEX ix_request_log_path ON dbops.request_log USING btree (path)` |
| ix_request_log_request_id | `CREATE INDEX ix_request_log_request_id ON dbops.request_log USING btree (request_id)` |
| pk_request_log | `CREATE UNIQUE INDEX pk_request_log ON dbops.request_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_request_log_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
