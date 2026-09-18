{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_task_runs.md" %}
# 📚 Tabella `fatturazione_lotti_task_runs`

> 📝 **Descrizione**
>
> Storico runtime per task eseguiti su lotto fatturazione

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| pipeline_id | bigint | YES |  |
| stato_doc_fiscale_id | integer | YES |  |
| task_code | character varying | NO |  |
| fase | character varying | YES |  |
| tentativo | smallint | NO | 1 |
| task_stato | character varying | NO | 'IN_ESECUZIONE'::character varying |
| started_at | timestamp with time zone | NO | clock_timestamp() |
| ended_at | timestamp with time zone | YES |  |
| error_code | character varying | YES |  |
| error_message | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| correlation_id | uuid | YES |  |
| cleanup_at | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatt_lotti_task_runs_task_stato |  |
| CHECK | chk_fatt_lotti_task_runs_timestamps |  |
| FOREIGN KEY | fk_fatt_lotti_task_runs_lotto | lotto_id |
| FOREIGN KEY | fk_fatt_lotti_task_runs_pipeline | pipeline_id |
| FOREIGN KEY | fk_fatt_lotti_task_runs_stato_doc | stato_doc_fiscale_id |
| PRIMARY KEY | pk_fatturazione_lotti_task_runs | id |
| UNIQUE | uq_fatt_lotti_task_runs_lotto_step_task_try | lotto_id, stato_doc_fiscale_id, task_code, tentativo |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_task_runs_correlation | `CREATE INDEX ix_task_runs_correlation ON vendite.fatturazione_lotti_task_runs USING btree (correlation_id) WHERE (correlation_id IS NOT NULL)` |
| pk_fatturazione_lotti_task_runs | `CREATE UNIQUE INDEX pk_fatturazione_lotti_task_runs ON vendite.fatturazione_lotti_task_runs USING btree (id)` |
| uq_fatt_lotti_task_runs_lotto_step_task_try | `CREATE UNIQUE INDEX uq_fatt_lotti_task_runs_lotto_step_task_try ON vendite.fatturazione_lotti_task_runs USING btree (lotto_id, stato_doc_fiscale_id, task_code, tentativo)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_task_runs_a10_fatturazione_pipeli_7a7b94 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'fatturazione_pipeline', 'attivo', 'pipeline_id', 'id')` |
| trg_fatturazione_lotti_task_runs_a10_fatturazione_pipeli_7a7b94 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'fatturazione_pipeline', 'attivo', 'pipeline_id', 'id')` |
| trg_fatturazione_lotti_task_runs_a10_stati_doc_fiscale_r_564554 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_task_runs_a10_stati_doc_fiscale_r_564554 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_task_runs_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_task_runs_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_task_runs_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_task_runs_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_task_runs_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
