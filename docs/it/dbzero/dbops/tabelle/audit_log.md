{% include-markdown "it/dbzero/dbops/manual/audit_log.md" %}
# 📚 Tabella `audit_log`

> 📝 **Descrizione**
>
> Il registro tecnico delle automazioni e degli strumenti DBA: una riga per esito di un lavoro (funzione, stato, durata, righe toccate, parametri e risultato, l'errore se c'e'). Lo stato e' OK, ERROR, DRYRUN o WARN (chk_audit_status). La porta di scrittura e' dbops.fn_audit_log_once; la riga nasce nella transazione del chiamante e si annulla con lei: un esito che deve sopravvivere a un errore sta in dbops.error_log. Ci scrivono solo funzioni di dbops e maintenance: lo presidia dbops.vw_audit_log_scrittori_fuori_perimetro, perche' il registro non deve contenere dati di dominio. La scadenza delle righe (cleanup_at) la governa la regola CLEANUP_AT di dbops.automation_rules_tbl.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| function_name | text | NO |  |
| executed_by | text | NO | CURRENT_USER |
| executed_at | timestamp with time zone | NO | now() |
| params | jsonb | YES |  |
| status | text | NO |  |
| message | text | YES |  |
| duration_ms | integer | YES |  |
| tx_id | uuid | YES |  |
| exec_mode | text | YES |  |
| parts | text[] | YES |  |
| rule_type | text | YES |  |
| dry_run | boolean | YES |  |
| sqlstate | text | YES |  |
| error_context | text | YES |  |
| rows_affected | integer | YES |  |
| host | text | YES |  |
| app_version | text | YES |  |
| result | jsonb | YES |  |
| cleanup_at | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_audit_status |  |
| PRIMARY KEY | pk_audit_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_audit_fn_ts | `CREATE INDEX ix_audit_fn_ts ON dbops.audit_log USING btree (function_name, executed_at DESC)` |
| ix_audit_log_cleanup_at | `CREATE INDEX ix_audit_log_cleanup_at ON dbops.audit_log USING btree (cleanup_at)` |
| ix_audit_params_gin | `CREATE INDEX ix_audit_params_gin ON dbops.audit_log USING gin (params)` |
| ix_audit_result_gin | `CREATE INDEX ix_audit_result_gin ON dbops.audit_log USING gin (result)` |
| ix_audit_status_ts | `CREATE INDEX ix_audit_status_ts ON dbops.audit_log USING btree (status, executed_at DESC)` |
| pk_audit_log | `CREATE UNIQUE INDEX pk_audit_log ON dbops.audit_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_audit_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_audit_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
