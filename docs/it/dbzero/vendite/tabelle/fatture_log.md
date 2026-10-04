{% include-markdown "it/dbzero/vendite/manual/fatture_log.md" %}
# 📚 Tabella `fatture_log`

> 📝 **Descrizione**
>
> Log anomalie fattura (warning/critical) con disabilitazione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| data_ora | timestamp with time zone | NO | clock_timestamp() |
| messaggio | text | NO |  |
| status | character(1) | NO | 'W'::bpchar |
| disabilitato | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| cleanup_at | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_log_status |  |
| FOREIGN KEY | fk_fatture_log_fattura | fattura_id |
| PRIMARY KEY | pk_fatture_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_log_data_ora | `CREATE INDEX ix_fatture_log_data_ora ON vendite.fatture_log USING btree (data_ora)` |
| ix_fatture_log_fattura_id | `CREATE INDEX ix_fatture_log_fattura_id ON vendite.fatture_log USING btree (fattura_id)` |
| pk_fatture_log | `CREATE UNIQUE INDEX pk_fatture_log ON vendite.fatture_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_log_a10_guard_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_logs_guard_delete()` |
| trg_fatture_log_a10_orario_reale_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_log_a10_orario_reale()` |
| trg_fatture_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_log_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_log_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |
| trg_fatture_log_z90_sync_critical_ad | AFTER | DELETE | `EXECUTE FUNCTION vendite.trgfn_fatture_log_sync_ad_stmt()` |
| trg_fatture_log_z90_sync_critical_ai | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_log_sync_ai_stmt()` |
| trg_fatture_log_z90_sync_critical_au | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_log_sync_au_stmt()` |

---
{% include-markdown "signature-core.md" %}
