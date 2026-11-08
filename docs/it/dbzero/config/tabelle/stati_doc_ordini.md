{% include-markdown "it/dbzero/config/manual/stati_doc_ordini.md" %}
# 📚 Tabella `stati_doc_ordini`

> 📝 **Descrizione**
>
> Dominio stati del documento ordini (codici stabili; descrizioni multilingua) .

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(32) | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| fase | character varying(20) | NO |  |
| esito | character varying(50) | YES |  |
| terminale | boolean | NO | false |
| pdf_mode | character varying | NO |  |
| pdf_allow_allegati | boolean | NO |  |
| is_abortito | boolean | NO | false |
| iniziale | boolean | NO | false |
| emissione | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_ordini_abortito_attivo |  |
| CHECK | chk_stati_doc_ordini_emissione_attivo |  |
| CHECK | chk_stati_doc_ordini_fase |  |
| CHECK | chk_stati_doc_ordini_iniziale_attivo |  |
| CHECK | chk_stati_doc_ordini_pdf_mode |  |
| CHECK | chk_stati_doc_ordini_terminale_chiuso |  |
| FOREIGN KEY | fk_stati_doc_ordini_esito | esito |
| PRIMARY KEY | pk_stati_doc_ordini | id |
| UNIQUE | uq_stati_doc_ordini_codice | codice |
| UNIQUE | uq_stati_doc_ordini_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_ordini_attivo | `CREATE INDEX ix_stati_doc_ordini_attivo ON config.stati_doc_ordini USING btree (attivo)` |
| pk_stati_doc_ordini | `CREATE UNIQUE INDEX pk_stati_doc_ordini ON config.stati_doc_ordini USING btree (id)` |
| uq_stati_doc_ordini_abortito | `CREATE UNIQUE INDEX uq_stati_doc_ordini_abortito ON config.stati_doc_ordini USING btree (is_abortito) WHERE is_abortito` |
| uq_stati_doc_ordini_codice | `CREATE UNIQUE INDEX uq_stati_doc_ordini_codice ON config.stati_doc_ordini USING btree (codice)` |
| uq_stati_doc_ordini_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_ordini_codice_interno ON config.stati_doc_ordini USING btree (codice_interno)` |
| uq_stati_doc_ordini_emissione | `CREATE UNIQUE INDEX uq_stati_doc_ordini_emissione ON config.stati_doc_ordini USING btree (emissione) WHERE emissione` |
| uq_stati_doc_ordini_iniziale | `CREATE UNIQUE INDEX uq_stati_doc_ordini_iniziale ON config.stati_doc_ordini USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_ordini_a10_guard_esito_verdetto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_ordini_a10_guard_esito_verdetto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_ordini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_ordini_a10_ordini_block_deact_upd_69c973 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'stato_doc_ordine_id', 'id', 'attivo')` |
| trg_stati_doc_ordini_a10_ordini_block_deact_upd_fddd2f | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini', 'stato_doc_ordine_id', 'id', 'attivo')` |
| trg_stati_doc_ordini_a10_ordini_righe_block_deact_upd_79f04e | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'stato_doc_ordine_id', 'id', 'attivo')` |
| trg_stati_doc_ordini_a10_ordini_righe_block_deact_upd_80a7ed | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini_righe', 'stato_doc_ordine_id', 'id', 'attivo')` |
| trg_stati_doc_ordini_a10_transizioni_stati_ordini_block__46935b | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_ordini', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_doc_ordini_a10_transizioni_stati_ordini_block__ad7ffa | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_ordini', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_doc_ordini_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_doc_ordini_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
