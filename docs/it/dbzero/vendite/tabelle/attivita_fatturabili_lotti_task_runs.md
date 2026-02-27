{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili_lotti_task_runs.md" %}
# 📚 Tabella `attivita_fatturabili_lotti_task_runs`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_attivita_id | bigint | NO |  |
| pipeline_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| branch_code | character varying | NO | 'DEFAULT'::character varying |
| task_code | character varying | NO |  |
| fase | character varying | YES |  |
| tentativo | smallint | NO | 1 |
| task_stato | character varying | NO | 'IN_ESECUZIONE'::character varying |
| block_scope | character varying | NO | 'BRANCH'::character varying |
| depends_on | jsonb | NO | '[]'::jsonb |
| started_at | timestamp with time zone | NO | now() |
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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_fatt_lotti_task_runs_block_scope |  |
| CHECK | chk_attivita_fatt_lotti_task_runs_task_stato |  |
| CHECK | chk_attivita_fatt_lotti_task_runs_timestamps |  |
| FOREIGN KEY | fk_attivita_fatt_lotti_task_runs_lotto | lotto_attivita_id |
| FOREIGN KEY | fk_attivita_fatt_lotti_task_runs_pipeline | pipeline_id |
| FOREIGN KEY | fk_attivita_fatt_lotti_task_runs_sorgente | sorgente_tipo_id |
| PRIMARY KEY | pk_attivita_fatt_lotti_task_runs | id |
| UNIQUE | uq_attivita_fatt_lotti_task_runs_lotto_pipe_branch_task_try | lotto_attivita_id, pipeline_id, branch_code, task_code, tentativo |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_attivita_fatt_lotti_task_runs | `CREATE UNIQUE INDEX pk_attivita_fatt_lotti_task_runs ON vendite.attivita_fatturabili_lotti_task_runs USING btree (id)` |
| uq_attivita_fatt_lotti_task_runs_lotto_pipe_branch_task_try | `CREATE UNIQUE INDEX uq_attivita_fatt_lotti_task_runs_lotto_pipe_branch_task_try ON vendite.attivita_fatturabili_lotti_task_runs USING btree (lotto_attivita_id, pipeline_id, branch_code, task_code, tentativo)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_fatturabili_lotti_task_runs_a10_attivita_fa_537c16 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'attivita_fatturabili_pipeline', 'attivo', 'pipeline_id')` |
| trg_attivita_fatturabili_lotti_task_runs_a10_attivita_fa_537c16 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'attivita_fatturabili_pipeline', 'attivo', 'pipeline_id')` |
| trg_attivita_fatturabili_lotti_task_runs_a10_sorgenti_re_a5f46f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_attivita_fatturabili_lotti_task_runs_a10_sorgenti_re_a5f46f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_attivita_fatturabili_lotti_task_runs_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_lotti_task_runs_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_lotti_task_runs_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_lotti_task_runs_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
