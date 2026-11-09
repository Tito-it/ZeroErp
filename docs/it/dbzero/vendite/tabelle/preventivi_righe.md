{% include-markdown "it/dbzero/vendite/manual/preventivi_righe.md" %}
# 📚 Tabella `preventivi_righe`

> 📝 **Descrizione**
>
> Righe preventivo: articoli, quantità, prezzi fotografati

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| preventivo_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying(200) | YES |  |
| quantita | numeric(18,6) | YES |  |
| prezzo_unitario | numeric(15,6) | NO |  |
| sconto_percentuale | numeric(7,4) | YES | 0 |
| iva_id | integer | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| ordine | smallint | YES | 0 |
| attivo | boolean | YES | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| qta_operativa | numeric(18,6) | NO |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric(18,6) | YES |  |
| stato_approvazione_prezzo | config.stato_approvazione_prezzo | YES |  |
| pratica_approvazione_prezzo_id | bigint | YES |  |
| tx_id | uuid | YES |  |
| natura_vendita_id | bigint | YES |  |
| data_consegna_richiesta_cliente | date | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| sorgente_riga | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_preventivi_righe_factor_to_base_finito |  |
| CHECK | chk_preventivi_righe_prezzo_unitario_finito |  |
| CHECK | chk_preventivi_righe_qta_operativa_finito |  |
| CHECK | chk_preventivi_righe_quantita_finito |  |
| CHECK | chk_preventivi_righe_sconto_percentuale_finito |  |
| CHECK | chk_preventivi_righe_sorgente_forma |  |
| CHECK | chk_prevrighe_qta_operativa_nonzero |  |
| CHECK | chk_prevrighe_sconto |  |
| FOREIGN KEY | fk_preventivi_righe_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_preventivi_vendita_r_uom_operativa | uom_operativa_id |
| FOREIGN KEY | fk_prevrighe_articoli | articolo_id |
| FOREIGN KEY | fk_prevrighe_iva | iva_id |
| FOREIGN KEY | fk_prevrighe_nature_vendita | natura_vendita_id |
| FOREIGN KEY | fk_prevrighe_pratica_approvazione_prezzo | pratica_approvazione_prezzo_id |
| FOREIGN KEY | fk_prevrighe_preventivi | preventivo_id |
| PRIMARY KEY | pk_preventivi_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_preventivi_righe_sorgente_riga | `CREATE INDEX ix_preventivi_righe_sorgente_riga ON vendite.preventivi_righe USING btree (sorgente_tipo_id, sorgente_riga) WHERE (sorgente_riga IS NOT NULL)` |
| ix_preventivi_righe_sorgente_uid | `CREATE INDEX ix_preventivi_righe_sorgente_uid ON vendite.preventivi_righe USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_uid IS NOT NULL)` |
| ix_vendite_preventivi_righe_articolo_id | `CREATE INDEX ix_vendite_preventivi_righe_articolo_id ON vendite.preventivi_righe USING btree (articolo_id)` |
| ix_vendite_preventivi_righe_preventivo_id | `CREATE INDEX ix_vendite_preventivi_righe_preventivo_id ON vendite.preventivi_righe USING btree (preventivo_id)` |
| ix_vendite_preventivi_righe_stato_approvazione | `CREATE INDEX ix_vendite_preventivi_righe_stato_approvazione ON vendite.preventivi_righe USING btree (stato_approvazione_prezzo) WHERE (stato_approvazione_prezzo IS NOT NULL)` |
| pk_preventivi_righe | `CREATE UNIQUE INDEX pk_preventivi_righe ON vendite.preventivi_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('PREVENTIVO', 'preventivo_id')` |
| trg_preventivi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('PREVENTIVO', 'preventivo_id')` |
| trg_preventivi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('PREVENTIVO', 'preventivo_id')` |
| trg_preventivi_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_preventivi_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_preventivi_righe_a10_guard_data_consegna_vs_doc_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_righe_guard_data_consegna('PREVENTIVO', 'preventivo_id')` |
| trg_preventivi_righe_a10_guard_data_consegna_vs_doc_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_righe_guard_data_consegna('PREVENTIVO', 'preventivo_id')` |
| trg_preventivi_righe_a10_guard_pending_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_pending('preventivo_id')` |
| trg_preventivi_righe_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('RIGA', 'BLOCCA')` |
| trg_preventivi_righe_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('RIGA', 'BLOCCA')` |
| trg_preventivi_righe_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_preventivi_righe_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_preventivi_righe_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('natura_vendita_id', 'E_RIGA_NATURA_VENDITA_IMMUTABILE')` |
| trg_preventivi_righe_a10_natura_vendita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_natura_vendita('ARTICOLO')` |
| trg_preventivi_righe_a10_natura_vendita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_natura_vendita('ARTICOLO')` |
| trg_preventivi_righe_a10_nature_vendita_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_preventivi_righe_a10_nature_vendita_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_preventivi_righe_a10_note_preventivo_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_preventivo', 'target_riga_id', 'id', 'attivo')` |
| trg_preventivi_righe_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'preventivo_riga_id', 'id', 'attivo')` |
| trg_preventivi_righe_a10_preventivi_righe_componenti_blo_4c13d0 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe_componenti', 'riga_preventivo_id', 'id', 'attivo')` |
| trg_preventivi_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', '', 'preventivi', 'preventivo_id', 'data')` |
| trg_preventivi_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', '', 'preventivi', 'preventivo_id', 'data')` |
| trg_preventivi_righe_a10_regole_articolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('PREVENTIVO', 'preventivo_id', 'sorgente_tipo_id')` |
| trg_preventivi_righe_a10_regole_articolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('PREVENTIVO', 'preventivo_id', 'sorgente_tipo_id')` |
| trg_preventivi_righe_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_preventivi_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_preventivi_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_preventivi_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_preventivi_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_preventivi_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_preventivi_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_preventivi_righe_z90_propaga_qta_componenti_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_propaga_qta('vendite', 'preventivi_righe_componenti', 'riga_preventivo_id')` |
| trg_preventivi_righe_z90_ricalcola_totali_dlt | AFTER | DELETE | `EXECUTE FUNCTION vendite.trgfn_preventivi_righe_ricalcola_totali()` |
| trg_preventivi_righe_z90_ricalcola_totali_ins | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_righe_ricalcola_totali()` |
| trg_preventivi_righe_z90_ricalcola_totali_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_righe_ricalcola_totali()` |

---
{% include-markdown "signature-core.md" %}
