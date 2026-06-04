{% include-markdown "it/dbzero/vendite/manual/ordini_righe.md" %}
# 📚 Tabella `ordini_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | NO |  |
| quantita | numeric | NO |  |
| prezzo_unitario | numeric | NO |  |
| sconto_perc | numeric | YES |  |
| iva_id | integer | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_riga | bigint | YES | 0 |
| stato_doc_ordine_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |
| attivo | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | check_ordini_righe_qta_operativa_pos |  |
| CHECK | chk_ordini_v_r_qta_pos |  |
| CHECK | chk_ordini_v_r_sconto_perc |  |
| CHECK | chk_ordini_v_r_uom_qta_operativa_copres |  |
| FOREIGN KEY | fk_ordini_vendita_r_uom_operativa | uom_operativa_id |
| FOREIGN KEY | fk_ordrig_articolo | articolo_id |
| FOREIGN KEY | fk_ordrig_iva | iva_id |
| FOREIGN KEY | fk_ordrig_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ordrig_stato_doc_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordrig_testata | ordine_id |
| PRIMARY KEY | pk_ordrig | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_ordini_righe_articolo_id | `CREATE INDEX ix_vendite_ordini_righe_articolo_id ON vendite.ordini_righe USING btree (articolo_id)` |
| ix_vendite_ordini_righe_ordine_id | `CREATE INDEX ix_vendite_ordini_righe_ordine_id ON vendite.ordini_righe USING btree (ordine_id)` |
| ix_vendite_ordini_righe_stato_doc_ordine_id | `CREATE INDEX ix_vendite_ordini_righe_stato_doc_ordine_id ON vendite.ordini_righe USING btree (stato_doc_ordine_id)` |
| pk_ordrig | `CREATE UNIQUE INDEX pk_ordrig ON vendite.ordini_righe USING btree (id)` |
| uq_ordini_righe_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_righe_v_sorgente_fk ON vendite.ordini_righe USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |
| uq_ordrig_riga_nr | `CREATE UNIQUE INDEX uq_ordrig_riga_nr ON vendite.ordini_righe USING btree (ordine_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ordini_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ordini_righe_a10_block_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_dlt_block_ordrig_ddtrig()` |
| trg_ordini_righe_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ordini_righe_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ordini_righe_a10_note_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_ordini', 'target_riga_id', 'id', 'attivo')` |
| trg_ordini_righe_a10_ordini_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe_componenti', 'riga_ordine_id', 'id', 'attivo')` |
| trg_ordini_righe_a10_ordini_righe_fulfillment_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe_fulfillment', 'ordine_riga_id', 'id', 'attivo')` |
| trg_ordini_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_ordini_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_ordini_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_righe_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_righe_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_ordini_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_ordini_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_z90_propaga_qta_componenti_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_propaga_qta('vendite', 'ordini_righe_componenti', 'riga_ordine_id')` |
| trg_ordini_righe_z90_ricalcola_totali_dlt | AFTER | DELETE | `EXECUTE FUNCTION vendite.trgfn_ordini_righe_ricalcola_totali()` |
| trg_ordini_righe_z90_ricalcola_totali_ins | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_righe_ricalcola_totali()` |
| trg_ordini_righe_z90_ricalcola_totali_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_righe_ricalcola_totali()` |
| trg_ordini_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_righe_id')` |
| trg_ordini_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_righe_id')` |

---
{% include-markdown "signature-core.md" %}
