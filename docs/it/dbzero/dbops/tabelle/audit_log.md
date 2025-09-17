{% include-markdown "it/dbzero/dbops/manual/audit_log.md" %}
# 📚 Tabella `audit_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| function_name | text | NO |  |
| executed_by | text | NO | 'CURRENT_USER'::text |
| executed_at | timestamp with time zone | NO | now() |
| params | jsonb | YES |  |
| status | text | NO |  |
| message | text | YES |  |
| duration_ms | integer | YES |  |
| tx_id | uuid | NO |  |
| exec_mode | text | YES |  |
| parts | ARRAY | YES |  |
| rule_type | text | YES |  |
| dry_run | boolean | YES |  |
| sqlstate | text | YES |  |
| error_context | text | YES |  |
| rows_affected | integer | YES |  |
| host | text | YES |  |
| app_version | text | YES |  |
| result | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_audit_status |  |
| PRIMARY KEY | pk_audit_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_audit_fn_ts | `CREATE INDEX ix_audit_fn_ts ON dbops.audit_log USING btree (function_name, executed_at DESC)` |
| ix_audit_params_gin | `CREATE INDEX ix_audit_params_gin ON dbops.audit_log USING gin (params)` |
| ix_audit_result_gin | `CREATE INDEX ix_audit_result_gin ON dbops.audit_log USING gin (result)` |
| ix_audit_status_ts | `CREATE INDEX ix_audit_status_ts ON dbops.audit_log USING btree (status, executed_at DESC)` |
| pk_audit_log | `CREATE UNIQUE INDEX pk_audit_log ON dbops.audit_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_assign_tx_id_audit_log | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_assign_tx_id_audit_log | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
