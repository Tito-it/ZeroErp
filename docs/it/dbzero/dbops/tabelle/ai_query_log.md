# 📚 Tabella `ai_query_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| request_id | uuid | NO |  |
| user_id | integer | NO |  |
| input_text | text | NO |  |
| tools_called | jsonb | YES |  |
| response_text | text | YES |  |
| provider | character varying | NO |  |
| model | character varying | NO |  |
| tokens_input | integer | YES |  |
| tokens_output | integer | YES |  |
| duration_ms | integer | YES |  |
| error_code | character varying | YES |  |
| cleanup_at | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_ai_query_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ai_query_log_cleanup_at | `CREATE INDEX ix_ai_query_log_cleanup_at ON dbops.ai_query_log USING btree (cleanup_at)` |
| ix_ai_query_log_data_insert | `CREATE INDEX ix_ai_query_log_data_insert ON dbops.ai_query_log USING btree (data_insert DESC)` |
| ix_ai_query_log_request_id | `CREATE INDEX ix_ai_query_log_request_id ON dbops.ai_query_log USING btree (request_id)` |
| ix_ai_query_log_user_id | `CREATE INDEX ix_ai_query_log_user_id ON dbops.ai_query_log USING btree (user_id)` |
| pk_ai_query_log | `CREATE UNIQUE INDEX pk_ai_query_log ON dbops.ai_query_log USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
