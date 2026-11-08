{% include-markdown "it/dbzero/config/manual/stati_doc_fiscale.md" %}
# 📚 Tabella `stati_doc_fiscale`

> 📝 **Descrizione**
>
> Dominio stati del documento fiscale (codici stabili; descrizioni multilingua).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| codice_interno | character varying(32) | NO |  |
| applica_lotto | boolean | NO | false |
| applica_fattura | boolean | NO | true |
| chiude_lotto | boolean | NO | false |
| fase | character varying(20) | NO |  |
| is_abortito | boolean | NO | false |
| congela_fiscale | boolean | NO | true |
| iniziale | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_fiscale_abortito_attivo |  |
| CHECK | chk_stati_doc_fiscale_fase |  |
| CHECK | chk_stati_doc_fiscale_iniziale_attivo |  |
| PRIMARY KEY | pk_stati_doc_fiscale | id |
| UNIQUE | uq_stati_doc_fiscale_codice | codice |
| UNIQUE | uq_stati_doc_fiscale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_fiscale_attivo | `CREATE INDEX ix_stati_doc_fiscale_attivo ON config.stati_doc_fiscale USING btree (attivo)` |
| pk_stati_doc_fiscale | `CREATE UNIQUE INDEX pk_stati_doc_fiscale ON config.stati_doc_fiscale USING btree (id)` |
| uq_stati_doc_fiscale_abortito | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_abortito ON config.stati_doc_fiscale USING btree (is_abortito) WHERE is_abortito` |
| uq_stati_doc_fiscale_chiude_lotto_true | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_chiude_lotto_true ON config.stati_doc_fiscale USING btree ((1)) WHERE (chiude_lotto IS TRUE)` |
| uq_stati_doc_fiscale_codice | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_codice ON config.stati_doc_fiscale USING btree (codice)` |
| uq_stati_doc_fiscale_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_codice_interno ON config.stati_doc_fiscale USING btree (codice_interno)` |
| uq_stati_doc_fiscale_iniziale | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_iniziale ON config.stati_doc_fiscale USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_fiscale_a10_fatturazione_lotti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti', 'stato_doc_fiscale_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a10_fatturazione_lotti_fatture_blo_e6dd7b | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti_fatture', 'stato_doc_fiscale_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a10_fatturazione_lotti_log_block_d_726218 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti_log', 'stato_doc_fiscale_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a10_fatturazione_lotti_task_runs_b_92a5a7 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti_task_runs', 'stato_doc_fiscale_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a10_fatturazione_pipeline_block_de_2b314c | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_pipeline', 'stato_doc_fiscale_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a10_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'stato_doc_fiscale_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_fiscale_a10_stati_doc_fiscale_transizioni__88be0f | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_fiscale_transizioni', 'stato_to_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a10_stati_doc_fiscale_transizioni__94ae32 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_fiscale_transizioni', 'stato_from_id', 'id', 'attivo')` |
| trg_stati_doc_fiscale_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_doc_fiscale_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_doc_fiscale_chiude_lotto_guard_iud | AFTER | DELETE | `EXECUTE FUNCTION config.trgfn_stati_doc_fiscale_chiude_lotto_guard()` |
| trg_stati_doc_fiscale_chiude_lotto_guard_iud | AFTER | UPDATE | `EXECUTE FUNCTION config.trgfn_stati_doc_fiscale_chiude_lotto_guard()` |
| trg_stati_doc_fiscale_chiude_lotto_guard_iud | AFTER | INSERT | `EXECUTE FUNCTION config.trgfn_stati_doc_fiscale_chiude_lotto_guard()` |

---
{% include-markdown "signature-core.md" %}
