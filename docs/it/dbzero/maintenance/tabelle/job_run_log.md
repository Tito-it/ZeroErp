{% include-markdown "it/dbzero/maintenance/manual/job_run_log.md" %}
# 📚 Tabella `job_run_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| jobname | text | NO |  |
| stepname | text | YES |  |
| started_at | timestamp with time zone | NO | clock_timestamp() |
| ended_at | timestamp with time zone | YES |  |
| ok | boolean | YES |  |
| rows_affected | bigint | YES |  |
| message | text | YES |  |
| error_code | text | YES |  |
| error_detail | text | YES |  |
| agent_host | text | YES | (inet_client_addr())::text |
| run_uuid | uuid | NO | uuidv7() |
| origine | character varying(16) | NO | 'PGAGENT'::character varying |
| meta | jsonb | NO | '{}'::jsonb |
| processo_codice | text | YES |  |
| auth_user_id | integer | YES |  |
| saltata | boolean | NO | false |
| ruolo_sessione | text | YES |  |
| sqlstate | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_job_run_log_origine |  |
| CHECK | chk_job_run_log_processo_dichiarato |  |
| CHECK | chk_job_run_log_saltata |  |
| CHECK | chk_job_run_log_sqlstate_forma |  |
| FOREIGN KEY | fk_job_run_log_processi | processo_codice |
| PRIMARY KEY | job_run_log_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| job_run_log_pkey | `CREATE UNIQUE INDEX job_run_log_pkey ON maintenance.job_run_log USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
