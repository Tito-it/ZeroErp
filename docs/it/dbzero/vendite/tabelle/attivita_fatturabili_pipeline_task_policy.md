{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili_pipeline_task_policy.md" %}
# 📚 Tabella `attivita_fatturabili_pipeline_task_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pipeline_id | bigint | NO |  |
| branch_code | character varying | NO | 'DEFAULT'::character varying |
| task_code | character varying | NO |  |
| annullabile | boolean | NO | true |
| resume_mode | character varying | NO | 'RESET_STEP'::character varying |
| block_scope | character varying | NO | 'BRANCH'::character varying |
| depends_on | jsonb | NO | '[]'::jsonb |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_fatt_pipeline_task_policy_block_scope |  |
| CHECK | chk_attivita_fatt_pipeline_task_policy_resume_mode |  |
| FOREIGN KEY | fk_attivita_fatt_pipeline_task_policy_pipeline | pipeline_id |
| PRIMARY KEY | pk_attivita_fatt_pipeline_task_policy | id |
| UNIQUE | uq_attivita_fatt_pipeline_task_policy_pipe_branch_task | pipeline_id, branch_code, task_code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_attivita_fatt_pipeline_task_policy | `CREATE UNIQUE INDEX pk_attivita_fatt_pipeline_task_policy ON vendite.attivita_fatturabili_pipeline_task_policy USING btree (id)` |
| uq_attivita_fatt_pipeline_task_policy_pipe_branch_task | `CREATE UNIQUE INDEX uq_attivita_fatt_pipeline_task_policy_pipe_branch_task ON vendite.attivita_fatturabili_pipeline_task_policy USING btree (pipeline_id, branch_code, task_code)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_fatturabili_pipeline_task_policy_a10_attivi_e5cbb8 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'attivita_fatturabili_pipeline', 'attivo', 'pipeline_id')` |
| trg_attivita_fatturabili_pipeline_task_policy_a10_attivi_e5cbb8 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'attivita_fatturabili_pipeline', 'attivo', 'pipeline_id')` |
| trg_attivita_fatturabili_pipeline_task_policy_audit_data_86cb4c | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_pipeline_task_policy_audit_data_86cb4c | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_pipeline_task_policy_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_pipeline_task_policy_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
