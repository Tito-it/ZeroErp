{% include-markdown "it/dbzero/vendite/manual/commesse_attivita_log.md" %}
# 📚 Tabella `commesse_attivita_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| commessa_attivita_id | bigint | NO |  |
| evento | character varying | NO |  |
| dettaglio | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_commesse_attivita_log_attivita | commessa_attivita_id |
| PRIMARY KEY | pk_commesse_attivita_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_attivita_log_attivita | `CREATE INDEX ix_commesse_attivita_log_attivita ON vendite.commesse_attivita_log USING btree (commessa_attivita_id)` |
| pk_commesse_attivita_log | `CREATE UNIQUE INDEX pk_commesse_attivita_log ON vendite.commesse_attivita_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_attivita_log_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_attivita_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_attivita_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_attivita_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
