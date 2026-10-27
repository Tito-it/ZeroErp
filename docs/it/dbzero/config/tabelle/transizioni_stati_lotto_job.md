{% include-markdown "it/dbzero/config/manual/transizioni_stati_lotto_job.md" %}
# 📚 Tabella `transizioni_stati_lotto_job`

> 📝 **Descrizione**
>
> Matrice dei passaggi dello stato del JOB di un lotto di fatturazione: una riga attiva = un passaggio ammesso. La sola regola dei passaggi di vendite.fatturazione_lotti.stato_lotto (F-4: prima era scritta due volte, nel backend e in una funzione morta, in disaccordo); la giudica il guard vendite.trgfn_fatturazione_lotti_guard_stato_job a ogni UPDATE che cambia lo stato. Riscrivere lo stesso stato non e' un passaggio (CHECK). COMPLETATO -&gt; ERRORE e' ammesso: un lotto gia' completato e rilanciato male si marca, «e' andata male» e' un fatto osservato (decisione di Tid del 2026-08-24); ERRORE -&gt; COMPLETATO no, la conclusione si guadagna con un giro. Seed dal CSV 80_data/sql/config/transizioni_stati_lotto_job.csv. Brief: brief-modello-documento-vendita §15 (F-4, Q-F4, Tid 2026-10-27).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_da_id | bigint | NO |  |
| stato_a_id | bigint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_transizioni_stati_lotto_job_non_riflessa |  |
| FOREIGN KEY | fk_transizioni_stati_lotto_job_a | stato_a_id |
| FOREIGN KEY | fk_transizioni_stati_lotto_job_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_lotto_job | id |
| UNIQUE | uq_transizioni_stati_lotto_job | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_lotto_job | `CREATE UNIQUE INDEX pk_transizioni_stati_lotto_job ON config.transizioni_stati_lotto_job USING btree (id)` |
| uq_transizioni_stati_lotto_job | `CREATE UNIQUE INDEX uq_transizioni_stati_lotto_job ON config.transizioni_stati_lotto_job USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_lotto_job_a10_stati_lotto_job_requ_935dc6 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_lotto_job', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_lotto_job_a10_stati_lotto_job_requ_935dc6 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_lotto_job', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_lotto_job_a10_stati_lotto_job_requ_ed7354 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_lotto_job', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_lotto_job_a10_stati_lotto_job_requ_ed7354 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_lotto_job', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_lotto_job_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_lotto_job_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
