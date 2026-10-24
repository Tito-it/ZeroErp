{% include-markdown "it/dbzero/config/manual/tipi_doc_fiscale.md" %}
# 📚 Tabella `tipi_doc_fiscale`

> 📝 **Descrizione**
>
> Dominio tipi di documento fiscale (codici stabili; descrizioni multilingua).

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
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_doc_fiscale | id |
| UNIQUE | uq_tipi_doc_fiscale_codice | codice |
| UNIQUE | uq_tipi_doc_fiscale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_doc_fiscale_attivo | `CREATE INDEX ix_tipi_doc_fiscale_attivo ON config.tipi_doc_fiscale USING btree (attivo)` |
| pk_tipi_doc_fiscale | `CREATE UNIQUE INDEX pk_tipi_doc_fiscale ON config.tipi_doc_fiscale USING btree (id)` |
| uq_tipi_doc_fiscale_codice | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_codice ON config.tipi_doc_fiscale USING btree (codice)` |
| uq_tipi_doc_fiscale_codice_interno | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_codice_interno ON config.tipi_doc_fiscale USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_doc_fiscale_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_fatturazione_lotti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_fatturazione_pipeline_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_pipeline', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_fatture_arrotondamenti_scope_bl_26b655 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_arrotondamenti_scope', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_fatture_fondi_fattura_source_bl_f0cf31 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_fondi_fattura_source', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_doc_fiscale_a10_sorgenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'sorgenti', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_a10_tipi_doc_fiscale_registri_block_482259 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'tipi_doc_fiscale_registri', 'tipo_doc_fiscale_id', 'id', 'attivo')` |
| trg_tipi_doc_fiscale_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_doc_fiscale_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_doc_fiscale_z90_provision_registri_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_coppie_fattura_provision_registri()` |
| trg_tipi_doc_fiscale_z90_provision_registri_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_coppie_fattura_provision_registri()` |

---
{% include-markdown "signature-core.md" %}
