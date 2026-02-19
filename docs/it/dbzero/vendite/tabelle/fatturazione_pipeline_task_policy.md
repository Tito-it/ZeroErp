{% include-markdown "it/dbzero/vendite/manual/fatturazione_pipeline_task_policy.md" %}
# 📚 Tabella `fatturazione_pipeline_task_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pipeline_id | bigint | NO |  |
| task_code | character varying | NO |  |
| annullabile | boolean | NO | true |
| resume_mode | character varying | NO | 'RESET_STEP'::character varying |
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
| CHECK | chk_fatt_pipeline_task_policy_resume_mode |  |
| FOREIGN KEY | fk_fatt_pipeline_task_policy_pipeline | pipeline_id |
| PRIMARY KEY | pk_fatturazione_pipeline_task_policy | id |
| UNIQUE | uq_fatt_pipeline_task_policy_pipeline_task | pipeline_id, task_code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_pipeline_task_policy | `CREATE UNIQUE INDEX pk_fatturazione_pipeline_task_policy ON vendite.fatturazione_pipeline_task_policy USING btree (id)` |
| uq_fatt_pipeline_task_policy_pipeline_task | `CREATE UNIQUE INDEX uq_fatt_pipeline_task_policy_pipeline_task ON vendite.fatturazione_pipeline_task_policy USING btree (pipeline_id, task_code)` |

---
{% include-markdown "signature-core.md" %}
