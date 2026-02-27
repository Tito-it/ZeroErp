{% include-markdown "it/dbzero/vendite/manual/event_log.md" %}
# 📚 Tabella `event_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| event_time | timestamp with time zone | NO | now() |
| domain | text | NO |  |
| entity_type | text | NO |  |
| entity_id | bigint | NO |  |
| event_code | text | NO |  |
| severity | text | NO | 'INFO'::text |
| correlation_id | uuid | YES |  |
| actor | text | YES |  |
| source | text | YES |  |
| payload | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_event_log_severity |  |
| PRIMARY KEY | pk_event_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_event_log_corr_time | `CREATE INDEX ix_event_log_corr_time ON vendite.event_log USING btree (correlation_id, event_time DESC)` |
| ix_event_log_domain_time | `CREATE INDEX ix_event_log_domain_time ON vendite.event_log USING btree (domain, event_time DESC)` |
| ix_event_log_entity_time | `CREATE INDEX ix_event_log_entity_time ON vendite.event_log USING btree (entity_type, entity_id, event_time DESC)` |
| pk_event_log | `CREATE UNIQUE INDEX pk_event_log ON vendite.event_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_event_log_append_only_ud | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_event_log_append_only()` |
| trg_event_log_append_only_ud | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_event_log_append_only()` |
| trg_event_log_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_event_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
