{% include-markdown "it/dbzero/maintenance/manual/job_run_log.md" %}
# 📚 Tabella `job_run_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('maintenance.job_run_log_id_seq'::regclass) |
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
| run_uuid | uuid | NO | gen_random_uuid() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | job_run_log_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| job_run_log_pkey | `CREATE UNIQUE INDEX job_run_log_pkey ON maintenance.job_run_log USING btree (id)` |
---
{% include-markdown "signature-core.md" %}
