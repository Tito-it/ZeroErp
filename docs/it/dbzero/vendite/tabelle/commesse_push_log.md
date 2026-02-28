{% include-markdown "it/dbzero/vendite/manual/commesse_push_log.md" %}
# 📚 Tabella `commesse_push_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| run_at | timestamp with time zone | NO | now() |
| dry_run | boolean | NO | false |
| source_types | ARRAY | YES |  |
| risultato | jsonb | NO | '{}'::jsonb |
| stato | character varying | NO |  |
| durata_ms | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_commesse_push_log_durata_ms |  |
| CHECK | chk_commesse_push_log_stato |  |
| PRIMARY KEY | pk_commesse_push_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_push_log_run_at | `CREATE INDEX ix_commesse_push_log_run_at ON vendite.commesse_push_log USING btree (run_at)` |
| pk_commesse_push_log | `CREATE UNIQUE INDEX pk_commesse_push_log ON vendite.commesse_push_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_push_log_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_push_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
