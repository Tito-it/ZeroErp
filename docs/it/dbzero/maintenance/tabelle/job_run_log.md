{% include-markdown "it/dbzero/maintenance/manual/job_run_log.md" %}
# 📚 Tabella `job_run_log`

> 📝 **Descrizione**
>
> Il giornale delle corse dei processi automatici: una riga per corsa, che sia di pgAgent, di un cron o di un management command (origine). Dice di quale processo e' la corsa (processo_codice, FK verso dbops.processi), quando e' partita e finita, se e' riuscita (ok), le righe toccate, il messaggio, e per un fallimento il codice d'errore piu' preciso disponibile (error_code) e lo SQLSTATE (sqlstate). Una corsa saltata per il lock occupato ha la sua riga, chiusa e senza esito (saltata). Lo scrivono solo maintenance.fn_run_and_log (le corse dei job), script.fn_job_run_start e script.fn_job_run_end (le corse headless) e maintenance.fn_job_run_log_failure (il verbale di un fallimento, scritto via dblink in un'altra sessione, cosi' sopravvive al rollback della corsa). Lo leggono i presidi maintenance.vw_job_run_da_guardare e maintenance.vw_job_run_da_superuser e il panorama dbops.vw_processi_programmazione.

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
