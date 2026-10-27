{% include-markdown "it/dbzero/config/manual/stati_lotto_job.md" %}
# 📚 Tabella `stati_lotto_job`

> 📝 **Descrizione**
>
> Vocabolario dello stato del JOB di un lotto di fatturazione (vendite.fatturazione_lotti.stato_lotto): IN_ESECUZIONE, COMPLETATO, ERRORE. E' l'asse del lavoro della pipeline, non lo stato fiscale del lotto (config.stati_doc_fiscale). La colonna del lotto porta il CODICE, con una FK su codice_interno (P-1). I passaggi ammessi in config.transizioni_stati_lotto_job. Seed dal CSV 80_data/sql/config/stati_lotto_job.csv. Brief: brief-modello-documento-vendita §15 (F-4, Q-F4, P-1, Tid 2026-10-27).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | text | NO |  |
| descrizione | character varying(120) | NO |  |
| ordine | smallint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_lotto_job | id |
| UNIQUE | uq_stati_lotto_job_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_lotto_job | `CREATE UNIQUE INDEX pk_stati_lotto_job ON config.stati_lotto_job USING btree (id)` |
| uq_stati_lotto_job_codice_interno | `CREATE UNIQUE INDEX uq_stati_lotto_job_codice_interno ON config.stati_lotto_job USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_lotto_job_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_lotto_job_a10_transizioni_stati_lotto_job_bloc_436a94 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_lotto_job', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_lotto_job_a10_transizioni_stati_lotto_job_bloc_a838d5 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_lotto_job', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_lotto_job_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_lotto_job_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
