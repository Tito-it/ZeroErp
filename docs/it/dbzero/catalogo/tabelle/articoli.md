{% include-markdown "it/dbzero/catalogo/manual/articoli.md" %}
# 📚 Tabella `articoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | YES |  |
| uom_id | bigint | NO |  |
| tipo_voce_id | bigint | YES |  |
| gruppo_voce_id | bigint | YES |  |
| spesa_id | bigint | YES |  |
| iva_id | bigint | YES |  |
| conto_contabile_vendita_id | bigint | YES |  |
| conto_contabile_acquisto_id | bigint | YES |  |
| is_composito | boolean | NO | false |
| requires_serial | boolean | NO | false |
| voce_utility | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| attivo | boolean | NO | true |
| note_target_tipo | character varying | YES |  |
| note_id | bigint | YES |  |
| is_solo_componente | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_articoli_note_target_tipo |  |
| FOREIGN KEY | fk_articoli_articoli_gruppi | gruppo_voce_id |
| FOREIGN KEY | fk_articoli_articoli_spesa | spesa_id |
| FOREIGN KEY | fk_articoli_articoli_tipologie | tipo_voce_id |
| FOREIGN KEY | fk_articoli_conti_contabili_acquisto | conto_contabile_acquisto_id |
| FOREIGN KEY | fk_articoli_conti_contabili_vendita | conto_contabile_vendita_id |
| FOREIGN KEY | fk_articoli_iva | iva_id |
| FOREIGN KEY | fk_articoli_note | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_note_1 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_note_2 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_unita_misura | uom_id |
| PRIMARY KEY | pk_articoli | id |
| UNIQUE | uq_articoli_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_catalogo_articoli_descrizione | `CREATE INDEX ix_catalogo_articoli_descrizione ON catalogo.articoli USING btree (descrizione) WITH (fillfactor='100', deduplicate_items='true')` |
| ix_catalogo_articoli_descrizione_trgm | `CREATE INDEX ix_catalogo_articoli_descrizione_trgm ON catalogo.articoli USING gin (descrizione gin_trgm_ops) WITH (fastupdate='true', gin_pending_list_limit='4194304')` |
| pk_articoli | `CREATE UNIQUE INDEX pk_articoli ON catalogo.articoli USING btree (id)` |
| uq_articoli_codice | `CREATE UNIQUE INDEX uq_articoli_codice ON catalogo.articoli USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_a10_articoli_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_componenti', 'componente_id', 'id', 'attivo')` |
| trg_articoli_a10_articoli_descrizioni_aggiuntive_block_d_315e77 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'articoli_descrizioni_aggiuntive', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_articoli_gruppi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id', 'id')` |
| trg_articoli_a10_articoli_gruppi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id', 'id')` |
| trg_articoli_a10_articoli_spesa_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id', 'id')` |
| trg_articoli_a10_articoli_spesa_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id', 'id')` |
| trg_articoli_a10_articoli_tipologie_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id', 'id')` |
| trg_articoli_a10_articoli_tipologie_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id', 'id')` |
| trg_articoli_a10_articoli_uom_operativa_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_uom_operativa', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_articolo_regole_fatturazione_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'articolo_regole_fatturazione', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'assets', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_contratti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_ddt_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_inventari_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_articoli_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_articoli_a10_listini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_note_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'note_articoli', 'target_id', 'id', 'attivo')` |
| trg_articoli_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_preventivi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_protect_codice_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')` |
| trg_articoli_a10_protect_uom_id_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('uom_id', 'CODICE_NON_MODIFICABILE')` |
| trg_articoli_a10_reservations_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'reservations', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_rettifiche_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_seed_uom_base_ins | AFTER | INSERT | `EXECUTE FUNCTION catalogo.trgfn_articoli_seed_uom_base()` |
| trg_articoli_a10_trasferimenti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'trasferimenti_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_articoli_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_id')` |
| trg_articoli_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_id')` |

---
{% include-markdown "signature-core.md" %}
