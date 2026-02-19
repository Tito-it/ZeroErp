{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_task_runs.md" %}
# 📚 Tabella `fatturazione_lotti_task_runs`

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
| pk_fatturazione_lotti_task_runs | `CREATE UNIQUE INDEX pk_fatturazione_lotti_task_runs ON vendite.fatturazione_lotti_task_runs USING btree (id)` |
| uq_fatt_lotti_task_runs_lotto_step_task_try | `CREATE UNIQUE INDEX uq_fatt_lotti_task_runs_lotto_step_task_try ON vendite.fatturazione_lotti_task_runs USING btree (lotto_id, stato_doc_fiscale_id, task_code, tentativo)` |

---
{% include-markdown "signature-core.md" %}
