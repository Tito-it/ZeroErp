{% include-markdown "it/dbzero/vendite/manual/resi_righe.md" %}
# 📚 Tabella `resi_righe`

> 📝 **Descrizione**
>
> Righe documento reso di vendita (brief-db-resi-vendita §4). Riga DDT sorgente NOT NULL, ordine_riga nullable (standalone), unita operativa mirror ddt_righe, tipo_reso per riga. Aggancio ri-consegna via ponte resi_righe_riconsegne. rev 2026-07-13.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| reso_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| ddt_riga_id | bigint | NO |  |
| ordine_riga_id | bigint | YES |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying(255) | NO |  |
| quantita | numeric | NO |  |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |
| tipo_reso_id | bigint | NO |  |
| motivo | character varying(255) | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_resi_righe_factor_to_base_finito |  |
| CHECK | chk_resi_righe_qta_operativa_finito |  |
| CHECK | chk_resi_righe_quantita_finito |  |
| CHECK | k_resi_righe_qta_operativa_pos |  |
| CHECK | k_resi_righe_qta_pos |  |
| FOREIGN KEY | fk_resi_righe_articolo | articolo_id |
| FOREIGN KEY | fk_resi_righe_ddt_riga | ddt_riga_id |
| FOREIGN KEY | fk_resi_righe_ordine_riga | ordine_riga_id |
| FOREIGN KEY | fk_resi_righe_testata | reso_id |
| FOREIGN KEY | fk_resi_righe_tipo_reso | tipo_reso_id |
| FOREIGN KEY | fk_resi_righe_uom_operativa | uom_operativa_id |
| PRIMARY KEY | pk_resi_righe | id |
| UNIQUE | uq_resi_righe_riga_nr | reso_id, riga_nr |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_righe_ddt_riga_id | `CREATE INDEX ix_resi_righe_ddt_riga_id ON vendite.resi_righe USING btree (ddt_riga_id)` |
| pk_resi_righe | `CREATE UNIQUE INDEX pk_resi_righe ON vendite.resi_righe USING btree (id)` |
| uq_resi_righe_riga_nr | `CREATE UNIQUE INDEX uq_resi_righe_riga_nr ON vendite.resi_righe USING btree (reso_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('RESO_VENDITA', 'reso_id')` |
| trg_resi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('RESO_VENDITA', 'reso_id')` |
| trg_resi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('RESO_VENDITA', 'reso_id')` |
| trg_resi_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_resi_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_resi_righe_a10_ddt_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_resi_righe_a10_ddt_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_resi_righe_a10_ordini_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ordini_righe', 'attivo', 'ordine_riga_id', 'id')` |
| trg_resi_righe_a10_ordini_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ordini_righe', 'attivo', 'ordine_riga_id', 'id')` |
| trg_resi_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true')` |
| trg_resi_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true')` |
| trg_resi_righe_a10_resi_righe_accrediti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe_accrediti', 'resi_riga_id', 'id', 'attivo')` |
| trg_resi_righe_a10_resi_righe_riconsegne_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe_riconsegne', 'resi_riga_id', 'id', 'attivo')` |
| trg_resi_righe_a10_resi_righe_rientri_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe_rientri', 'resi_riga_id', 'id', 'attivo')` |
| trg_resi_righe_a10_resi_righe_rinunce_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe_rinunce', 'resi_riga_id', 'id', 'attivo')` |
| trg_resi_righe_a10_tipi_reso_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_reso', 'attivo', 'tipo_reso_id', 'id')` |
| trg_resi_righe_a10_tipi_reso_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_reso', 'attivo', 'tipo_reso_id', 'id')` |
| trg_resi_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_resi_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_resi_righe_a20_guard_origine_coerente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_righe_guard_origine_coerente()` |
| trg_resi_righe_a20_guard_origine_coerente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_righe_guard_origine_coerente()` |
| trg_resi_righe_a20_guard_quantita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_righe_guard_quantita()` |
| trg_resi_righe_a20_guard_quantita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_righe_guard_quantita()` |
| trg_resi_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_id')` |
| trg_resi_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_id')` |

---
{% include-markdown "signature-core.md" %}
