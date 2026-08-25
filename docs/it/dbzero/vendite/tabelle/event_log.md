{% include-markdown "it/dbzero/vendite/manual/event_log.md" %}
# 📚 Tabella `event_log`

> 📝 **Descrizione**
>
> Event log unificato append-only per timeline cross-dominio (pipeline, commesse, sdi, fatture).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| event_time | timestamp with time zone | NO | clock_timestamp() |
| entity_type | text | NO |  |
| entity_id | bigint | NO |  |
| event_code | text | NO |  |
| severity | text | NO | 'INFO'::text |
| correlation_id | uuid | YES |  |
| payload | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| auth_user_id | bigint | YES |  |
| tx_id | uuid | YES |  |
| cleanup_at | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_event_log_severity |  |
| FOREIGN KEY | fk_event_log_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_event_log_tipo_entita | entity_type |
| PRIMARY KEY | pk_event_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_event_log_corr_time | `CREATE INDEX ix_event_log_corr_time ON vendite.event_log USING btree (correlation_id, event_time DESC)` |
| ix_event_log_entity_time | `CREATE INDEX ix_event_log_entity_time ON vendite.event_log USING btree (entity_type, entity_id, event_time DESC)` |
| pk_event_log | `CREATE UNIQUE INDEX pk_event_log ON vendite.event_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_event_log_a10_deriva_scope_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_event_log_deriva_scope()` |
| trg_event_log_append_only_ud | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_event_log_append_only()` |
| trg_event_log_append_only_ud | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_event_log_append_only()` |
| trg_event_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_event_log_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_event_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_event_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
