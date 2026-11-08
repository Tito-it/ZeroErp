{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_log.md" %}
# 📚 Tabella `fatturazione_lotti_log`

> 📝 **Descrizione**
>
> Log per processi lotto fatturazione (warning/critical).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| data_ora | timestamp with time zone | NO | clock_timestamp() |
| messaggio | text | NO |  |
| status | character(1) | NO | 'W'::bpchar |
| disabilitato | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| fase | text | YES |  |
| stato_doc_fiscale_id | bigint | YES |  |
| tipo_lotto | text | YES |  |
| stato_operativo | text | YES |  |
| tx_id | uuid | YES |  |
| gruppo_key | text | YES |  |
| cleanup_at | timestamp with time zone | YES |  |
| commessa_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lotti_log_stato_operativo |  |
| CHECK | chk_fatturazione_lotti_log_status |  |
| CHECK | chk_fatturazione_lotti_log_tipo_lotto |  |
| FOREIGN KEY | fk_fatturazione_lotti_log_lotto | lotto_id |
| FOREIGN KEY | fk_fatturazione_lotti_log_stato_doc_fiscale | stato_doc_fiscale_id |
| PRIMARY KEY | pk_fatturazione_lotti_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatturazione_lotti_log_data_ora | `CREATE INDEX ix_fatturazione_lotti_log_data_ora ON vendite.fatturazione_lotti_log USING btree (data_ora)` |
| ix_fatturazione_lotti_log_lotto_id | `CREATE INDEX ix_fatturazione_lotti_log_lotto_id ON vendite.fatturazione_lotti_log USING btree (lotto_id)` |
| pk_fatturazione_lotti_log | `CREATE UNIQUE INDEX pk_fatturazione_lotti_log ON vendite.fatturazione_lotti_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_log_a10_guard_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_logs_guard_delete()` |
| trg_fatturazione_lotti_log_a10_stati_doc_fiscale_require_48d164 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_log_a10_stati_doc_fiscale_require_48d164 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_log_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_log_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
