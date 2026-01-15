{% include-markdown "it/dbzero/catalogo/manual/articoli.md" %}
# 📚 Tabella `articoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | YES |  |
| uom_id | bigint | YES |  |
| tipo_voce_id | bigint | YES |  |
| gruppo_voce_id | bigint | YES |  |
| spesa_id | bigint | YES |  |
| iva_id | bigint | YES |  |
| conto_contabile_vendita_id | bigint | YES |  |
| conto_contabile_acquisto_id | bigint | YES |  |
| is_composito | boolean | NO | false |
| requires_serial | boolean | NO | false |
| voce_utility | boolean | NO | false |
| fondo_fattura | boolean | NO | false |
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
| FOREIGN KEY | fk_articoli_note | note_id, note_target_tipo |
| FOREIGN KEY | fk_articoli_note_1 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_note_2 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_unita_misura | uom_id |
| PRIMARY KEY | pk_articoli | id |
| UNIQUE | uq_articoli_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_articoli | `CREATE UNIQUE INDEX pk_articoli ON catalogo.articoli USING btree (id)` |
| uq_articoli_codice | `CREATE UNIQUE INDEX uq_articoli_codice ON catalogo.articoli USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_a10_articoli_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_componenti', 'componente_id', 'id')` |
| trg_articoli_a10_articoli_descrizioni_aggiuntive_block_d_315e77 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'articoli_descrizioni_aggiuntive', 'articolo_id', 'id')` |
| trg_articoli_a10_articoli_gruppi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id')` |
| trg_articoli_a10_articoli_gruppi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id')` |
| trg_articoli_a10_articoli_spesa_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id')` |
| trg_articoli_a10_articoli_spesa_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id')` |
| trg_articoli_a10_articoli_tipologie_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id')` |
| trg_articoli_a10_articoli_tipologie_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id')` |
| trg_articoli_a10_articoli_uom_operativa_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_uom_operativa', 'articolo_id', 'id')` |
| trg_articoli_a10_articolo_regole_fatturazione_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'articolo_regole_fatturazione', 'articolo_id', 'id')` |
| trg_articoli_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'articolo_id', 'id')` |
| trg_articoli_a10_contratti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe', 'articolo_id', 'id')` |
| trg_articoli_a10_ddt_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe', 'articolo_id', 'id')` |
| trg_articoli_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'articolo_id', 'id')` |
| trg_articoli_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id')` |
| trg_articoli_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id')` |
| trg_articoli_a10_note_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'note_articoli', 'target_id', 'id')` |
| trg_articoli_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'articolo_id', 'id')` |
| trg_articoli_a10_preventivi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe', 'articolo_id', 'id')` |
| trg_articoli_a10_protect_codice_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')` |
| trg_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_articoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_id')` |
| trg_articoli_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_id')` |

---
{% include-markdown "signature-core.md" %}
