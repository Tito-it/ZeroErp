{% include-markdown "it/dbzero/catalogo/manual/articoli.md" %}
# 📚 Tabella `articoli`

> 📝 **Descrizione**
>
> Anagrafica articoli/voci (generica, per utilities e non).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| codice | character varying(50) | NO |  |
| descrizione | character varying(150) | NO |  |
| descrizione_breve | character varying(80) | YES |  |
| uom_id | bigint | NO |  |
| tipo_voce_id | bigint | YES |  |
| gruppo_voce_id | bigint | YES |  |
| spesa_id | bigint | YES |  |
| iva_id | bigint | YES |  |
| conto_contabile_vendita_id | bigint | YES |  |
| conto_contabile_acquisto_id | bigint | YES |  |
| is_composito | boolean | NO | false |
| requires_serial | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| attivo | boolean | NO | true |
| note_target_tipo | character varying(50) | YES |  |
| note_id | bigint | YES |  |
| is_solo_componente | boolean | NO | false |
| listino_tipologia_id | smallint | YES |  |
| natura_vendita_id | bigint | NO | 1 |
| causale_onere_id | bigint | YES |  |
| modo_approvvigionamento_id | bigint | NO | 1 |
| gestito_a_magazzino | boolean | NO | false |
| lead_time_giorni | integer | YES |  |
| requires_lotto | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_articoli_lead_time_giorni_non_negativo |  |
| CHECK | chk_articoli_note_target_tipo |  |
| FOREIGN KEY | fk_articoli_articoli_gruppi | gruppo_voce_id |
| FOREIGN KEY | fk_articoli_articoli_spesa | spesa_id |
| FOREIGN KEY | fk_articoli_articoli_tipologie | tipo_voce_id |
| FOREIGN KEY | fk_articoli_causale_onere | causale_onere_id |
| FOREIGN KEY | fk_articoli_conti_contabili_acquisto | conto_contabile_acquisto_id |
| FOREIGN KEY | fk_articoli_conti_contabili_vendita | conto_contabile_vendita_id |
| FOREIGN KEY | fk_articoli_iva | iva_id |
| FOREIGN KEY | fk_articoli_listino_tipologia | listino_tipologia_id |
| FOREIGN KEY | fk_articoli_modi_approvvigionamento | modo_approvvigionamento_id |
| FOREIGN KEY | fk_articoli_nature_vendita | natura_vendita_id |
| FOREIGN KEY | fk_articoli_note | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_note_1 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_note_2 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_unita_misura | uom_id |
| PRIMARY KEY | pk_articoli | id |
| UNIQUE | uq_articoli_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_listino_tipologia | `CREATE INDEX ix_articoli_listino_tipologia ON catalogo.articoli USING btree (listino_tipologia_id)` |
| ix_catalogo_articoli_descrizione | `CREATE INDEX ix_catalogo_articoli_descrizione ON catalogo.articoli USING btree (descrizione) WITH (fillfactor='100', deduplicate_items='true')` |
| ix_catalogo_articoli_descrizione_trgm | `CREATE INDEX ix_catalogo_articoli_descrizione_trgm ON catalogo.articoli USING gin (descrizione gin_trgm_ops) WITH (fastupdate='true', gin_pending_list_limit='4194304')` |
| pk_articoli | `CREATE UNIQUE INDEX pk_articoli ON catalogo.articoli USING btree (id)` |
| uq_articoli_causale_onere | `CREATE UNIQUE INDEX uq_articoli_causale_onere ON catalogo.articoli USING btree (causale_onere_id) WHERE (causale_onere_id IS NOT NULL)` |
| uq_articoli_codice | `CREATE UNIQUE INDEX uq_articoli_codice ON catalogo.articoli USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_a10_articoli_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_componenti', 'componente_id', 'id', 'attivo')` |
| trg_articoli_a10_articoli_descrizioni_aggiuntive_block_d_315e77 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'articoli_descrizioni_aggiuntive', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_articoli_gruppi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id', 'id')` |
| trg_articoli_a10_articoli_gruppi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_gruppi', 'attivo', 'gruppo_voce_id', 'id')` |
| trg_articoli_a10_articoli_spesa_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id', 'id')` |
| trg_articoli_a10_articoli_spesa_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_spesa', 'attivo', 'spesa_id', 'id')` |
| trg_articoli_a10_articoli_tipologie_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id', 'id')` |
| trg_articoli_a10_articoli_tipologie_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'articoli_tipologie', 'attivo', 'tipo_voce_id', 'id')` |
| trg_articoli_a10_articoli_uom_operativa_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_uom_operativa', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_articolo_regole_fatturazione_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'articolo_regole_fatturazione', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'assets', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_causali_onere_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_onere', 'attivo', 'causale_onere_id', 'id')` |
| trg_articoli_a10_causali_onere_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_onere', 'attivo', 'causale_onere_id', 'id')` |
| trg_articoli_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_contratti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_contratti_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe_componenti', 'componente_id', 'id', 'attivo')` |
| trg_articoli_a10_ddt_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_ddt_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_componenti', 'componente_id', 'id', 'attivo')` |
| trg_articoli_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_guard_flags_struttura_bom_attiva_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva()` |
| trg_articoli_a10_guard_iva_bom_attiva_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_guard_iva_bom_attiva()` |
| trg_articoli_a10_guard_listino_se_composito_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_guard_listino_se_composito()` |
| trg_articoli_a10_guard_onere_natura_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_guard_onere_natura()` |
| trg_articoli_a10_guard_onere_natura_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION catalogo.trgfn_articoli_guard_onere_natura()` |
| trg_articoli_a10_guard_struttura_se_usato_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_guard_struttura_se_usato()` |
| trg_articoli_a10_inventari_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_articoli_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_articoli_a10_listini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_listini_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe_componenti', 'articolo_figlio_id', 'id', 'attivo')` |
| trg_articoli_a10_listini_tipologie_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'listino_tipologia_id', 'id')` |
| trg_articoli_a10_listini_tipologie_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'listino_tipologia_id', 'id')` |
| trg_articoli_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE', 'uom_id', 'E_CODICE_NON_MODIFICABILE')` |
| trg_articoli_a10_lotti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'lotti', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_modi_approvvigionamento_require_attivo__1ad7bd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modi_approvvigionamento', 'attivo', 'modo_approvvigionamento_id', 'id')` |
| trg_articoli_a10_modi_approvvigionamento_require_attivo__1ad7bd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modi_approvvigionamento', 'attivo', 'modo_approvvigionamento_id', 'id')` |
| trg_articoli_a10_movimenti_attesi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti_attesi', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_nature_vendita_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_articoli_a10_nature_vendita_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_articoli_a10_note_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'note_articoli', 'target_id', 'id', 'attivo')` |
| trg_articoli_a10_offerte_commerciali_eccezioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali_eccezioni', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_offerte_commerciali_eccezioni_component_796df0 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali_eccezioni_componenti', 'componente_id', 'id', 'attivo')` |
| trg_articoli_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_ordini_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe_componenti', 'componente_id', 'id', 'attivo')` |
| trg_articoli_a10_preventivi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_preventivi_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe_componenti', 'componente_id', 'id', 'attivo')` |
| trg_articoli_a10_promo_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'promo_articoli', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_resi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_rettifiche_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_seed_uom_base_ins | AFTER | INSERT | `EXECUTE FUNCTION catalogo.trgfn_articoli_seed_uom_base()` |
| trg_articoli_a10_soggetti_titoli_iva_ambiti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva_ambiti', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_trasferimenti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'trasferimenti_righe', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_articoli_a10_valore_giacenza_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'valore_giacenza', 'articolo_id', 'id', 'attivo')` |
| trg_articoli_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_id')` |
| trg_articoli_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_id')` |

---
{% include-markdown "signature-core.md" %}
