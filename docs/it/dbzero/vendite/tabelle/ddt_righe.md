{% include-markdown "it/dbzero/vendite/manual/ddt_righe.md" %}
# 📚 Tabella `ddt_righe`

> 📝 **Descrizione**
>
> Righe DDT di vendita (merce/beni).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ddt_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying(150) | NO |  |
| quantita | numeric(18,6) | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| qta_operativa | numeric(18,6) | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric(18,6) | NO | 1 |
| attivo | boolean | NO | true |
| prezzo_unitario | numeric | YES |  |
| sconto_percentuale | numeric | YES |  |
| iva_id | integer | YES |  |
| natura_vendita_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ddt_righe_factor_to_base_finito |  |
| CHECK | chk_ddt_righe_prezzo_unitario_finito |  |
| CHECK | chk_ddt_righe_qta_operativa_finito |  |
| CHECK | chk_ddt_righe_quantita_finito |  |
| CHECK | chk_ddt_righe_sconto_percentuale_finito |  |
| CHECK | k_ddt_righe_qta_operativa_pos |  |
| CHECK | k_ddt_righe_qta_pos |  |
| FOREIGN KEY | fk_ddt_vendita_r_articolo | articolo_id |
| FOREIGN KEY | fk_ddt_vendita_r_iva | iva_id |
| FOREIGN KEY | fk_ddt_vendita_r_natura_vendita | natura_vendita_id |
| FOREIGN KEY | fk_ddt_vendita_r_testata | ddt_id |
| FOREIGN KEY | fk_ddt_vendita_r_uom_operativa | uom_operativa_id |
| PRIMARY KEY | pk_ddtvr | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_ddt_righe_articolo_id | `CREATE INDEX ix_vendite_ddt_righe_articolo_id ON vendite.ddt_righe USING btree (articolo_id)` |
| pk_ddtvr | `CREATE UNIQUE INDEX pk_ddtvr ON vendite.ddt_righe USING btree (id)` |
| uq_ddt_vendita_r_riga_nr | `CREATE UNIQUE INDEX uq_ddt_vendita_r_riga_nr ON vendite.ddt_righe USING btree (ddt_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_id')` |
| trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_id')` |
| trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_id')` |
| trg_ddt_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ddt_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ddt_righe_a10_block_ddt_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_dlt_block_ordrig_ddtrig()` |
| trg_ddt_righe_a10_ddt_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_componenti', 'riga_ddt_id', 'id', 'attivo')` |
| trg_ddt_righe_a10_ddt_righe_prelievi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_prelievi', 'ddt_riga_id', 'id', 'attivo')` |
| trg_ddt_righe_a10_guard_riga_evasa_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_righe_guard_riga_evasa()` |
| trg_ddt_righe_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ddt_righe_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ddt_righe_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('natura_vendita_id', 'E_RIGA_NATURA_VENDITA_IMMUTABILE')` |
| trg_ddt_righe_a10_natura_vendita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_natura_vendita('CHIAMANTE')` |
| trg_ddt_righe_a10_natura_vendita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_natura_vendita('CHIAMANTE')` |
| trg_ddt_righe_a10_nature_vendita_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_ddt_righe_a10_nature_vendita_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_ddt_righe_a10_note_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_ddt', 'target_riga_id', 'id', 'attivo')` |
| trg_ddt_righe_a10_ordini_righe_fulfillment_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe_fulfillment', 'ddt_riga_id', 'id', 'attivo')` |
| trg_ddt_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true')` |
| trg_ddt_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true')` |
| trg_ddt_righe_a10_regole_articolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('DDT_VENDITA', 'ddt_id')` |
| trg_ddt_righe_a10_regole_articolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('DDT_VENDITA', 'ddt_id')` |
| trg_ddt_righe_a10_resi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe', 'ddt_riga_id', 'id', 'attivo')` |
| trg_ddt_righe_a10_resi_righe_riconsegne_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe_riconsegne', 'ddt_riga_id', 'id', 'attivo')` |
| trg_ddt_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_ddt_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_ddt_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_righe_z90_propaga_qta_componenti_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_propaga_qta('vendite', 'ddt_righe_componenti', 'riga_ddt_id')` |
| trg_ddt_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_righe_id')` |
| trg_ddt_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_righe_id')` |

---
{% include-markdown "signature-core.md" %}
