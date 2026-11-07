{% include-markdown "it/dbzero/vendite/manual/commesse_attivita.md" %}
# 📚 Tabella `commesse_attivita`

> 📝 **Descrizione**
>
> Righe operative/fatturabili commessa.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| commessa_id | bigint | NO |  |
| segment_key | character varying(128) | NO |  |
| articolo_id | uuid | NO |  |
| istanza_utility_id | bigint | NO |  |
| data_attivita | date | NO |  |
| uom_id | bigint | NO |  |
| quantita | numeric(18,6) | NO |  |
| qta_operativa | numeric(18,6) | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric(18,10) | NO | 1 |
| competenza_mese | date | NO |  |
| competenza_dal | date | NO |  |
| competenza_al | date | NO |  |
| posticipa_al | date | YES |  |
| tipo_doc_fiscale_id | bigint | YES |  |
| valuta_id | integer | YES |  |
| area_geografica_id | bigint | YES |  |
| listino_versione_id | bigint | YES |  |
| prezzo_snapshot | numeric(22,10) | NO |  |
| prezzo_bloccato | boolean | NO | false |
| pricing_mode | character varying(16) | NO | 'FIXED'::character varying |
| prezzo_da_riallineare | boolean | NO | false |
| stato_approvazione | character varying(16) | NO | 'BOZZA'::character varying |
| stato_emissione | character varying(16) | NO | 'NON_EMESSA'::character varying |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| listino_riga_id | bigint | YES |  |
| prezzo_base_snapshot | numeric(22,10) | YES |  |
| origine_prezzo | character varying(32) | YES |  |
| tipo_variazione_applicata | character varying(16) | YES |  |
| valore_variazione_applicata | numeric(10,4) | YES |  |
| promo_id | bigint | YES |  |
| contratto_id | bigint | YES |  |
| categoria_cliente_id_snapshot | smallint | YES |  |
| classe_utenza_id_snapshot | integer | YES |  |
| tipo_movimento | character varying(32) | NO | 'NORMALE'::character varying |
| causale_onere_id | bigint | YES |  |
| natura_doc_id | bigint | NO | config.fn_get_natura_doc_fiscale_id('FATTURA'::character varying) |
| fattura_riga_rettificata_id | bigint | YES |  |
| segment_base | character varying(128) | NO |  |
| sorgente_id | bigint | YES |  |
| sorgente_riga | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_commesse_attivita_causale_onere |  |
| CHECK | chk_commesse_attivita_comp_mese_primo |  |
| CHECK | chk_commesse_attivita_comp_range |  |
| CHECK | chk_commesse_attivita_factor_to_base |  |
| CHECK | chk_commesse_attivita_factor_to_base_finito |  |
| CHECK | chk_commesse_attivita_listino_riga_con_versione |  |
| CHECK | chk_commesse_attivita_origine_prezzo |  |
| CHECK | chk_commesse_attivita_posticipa |  |
| CHECK | chk_commesse_attivita_prezzo |  |
| CHECK | chk_commesse_attivita_prezzo_base_snapshot_finito |  |
| CHECK | chk_commesse_attivita_prezzo_snapshot_finito |  |
| CHECK | chk_commesse_attivita_pricing_mode |  |
| CHECK | chk_commesse_attivita_qta_operativa_finito |  |
| CHECK | chk_commesse_attivita_quantita_finito |  |
| CHECK | chk_commesse_attivita_rettificata_e_rettifica |  |
| CHECK | chk_commesse_attivita_senza_sorgente_onere_rettifica |  |
| CHECK | chk_commesse_attivita_sorgente_forma |  |
| CHECK | chk_commesse_attivita_stato_approvazione |  |
| CHECK | chk_commesse_attivita_stato_emissione |  |
| CHECK | chk_commesse_attivita_tipo_doc_emittibile |  |
| CHECK | chk_commesse_attivita_tipo_movimento |  |
| CHECK | chk_commesse_attivita_tipo_variazione_applicata |  |
| CHECK | chk_commesse_attivita_valore_variazione_applicata_finito |  |
| FOREIGN KEY | commesse_attivita_listino_riga_id_fkey | listino_riga_id |
| FOREIGN KEY | fk_commesse_attivita_area_geo | area_geografica_id |
| FOREIGN KEY | fk_commesse_attivita_articolo | articolo_id |
| FOREIGN KEY | fk_commesse_attivita_categoria_cliente_snapshot | categoria_cliente_id_snapshot |
| FOREIGN KEY | fk_commesse_attivita_causale_onere | causale_onere_id |
| FOREIGN KEY | fk_commesse_attivita_classe_utenza_snapshot | classe_utenza_id_snapshot |
| FOREIGN KEY | fk_commesse_attivita_commessa | commessa_id |
| FOREIGN KEY | fk_commesse_attivita_contratto | contratto_id |
| FOREIGN KEY | fk_commesse_attivita_fattura_riga_rettificata | fattura_riga_rettificata_id |
| FOREIGN KEY | fk_commesse_attivita_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_commesse_attivita_listino_versione | listino_versione_id |
| FOREIGN KEY | fk_commesse_attivita_natura_doc | natura_doc_id |
| FOREIGN KEY | fk_commesse_attivita_promo | promo_id |
| FOREIGN KEY | fk_commesse_attivita_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_commesse_attivita_tipo_doc | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_commesse_attivita_uom | uom_id |
| FOREIGN KEY | fk_commesse_attivita_uom_operativa | uom_operativa_id |
| FOREIGN KEY | fk_commesse_attivita_valuta | valuta_id |
| PRIMARY KEY | pk_commesse_attivita | id |
| UNIQUE | uq_commesse_attivita_commessa_segment | commessa_id, segment_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_attivita_commessa_stati | `CREATE INDEX ix_commesse_attivita_commessa_stati ON vendite.commesse_attivita USING btree (commessa_id, stato_approvazione, stato_emissione)` |
| ix_commesse_attivita_fattura_riga_rettificata_id | `CREATE INDEX ix_commesse_attivita_fattura_riga_rettificata_id ON vendite.commesse_attivita USING btree (fattura_riga_rettificata_id) WHERE (fattura_riga_rettificata_id IS NOT NULL)` |
| ix_commesse_attivita_lane_candidate | `CREATE INDEX ix_commesse_attivita_lane_candidate ON vendite.commesse_attivita USING btree (commessa_id, competenza_mese, tipo_doc_fiscale_id) WHERE (((stato_emissione)::text = 'NON_EMESSA'::text) AND ((stato_approvazione)::text = 'APPROVATA'::text) AND (tipo_doc_fiscale_id IS NOT NULL))` |
| ix_commesse_attivita_listino_riga_id | `CREATE INDEX ix_commesse_attivita_listino_riga_id ON vendite.commesse_attivita USING btree (listino_riga_id) WHERE (listino_riga_id IS NOT NULL)` |
| ix_commesse_attivita_origine_prezzo | `CREATE INDEX ix_commesse_attivita_origine_prezzo ON vendite.commesse_attivita USING btree (origine_prezzo)` |
| ix_commesse_attivita_segment_base | `CREATE INDEX ix_commesse_attivita_segment_base ON vendite.commesse_attivita USING btree (segment_base)` |
| ix_commesse_attivita_segment_key | `CREATE INDEX ix_commesse_attivita_segment_key ON vendite.commesse_attivita USING btree (segment_key varchar_pattern_ops)` |
| ix_commesse_attivita_sorgente_id | `CREATE INDEX ix_commesse_attivita_sorgente_id ON vendite.commesse_attivita USING btree (sorgente_tipo_id, sorgente_id) WHERE (sorgente_id IS NOT NULL)` |
| ix_commesse_attivita_sorgente_riga | `CREATE INDEX ix_commesse_attivita_sorgente_riga ON vendite.commesse_attivita USING btree (sorgente_tipo_id, sorgente_riga) WHERE (sorgente_riga IS NOT NULL)` |
| ix_commesse_attivita_sorgente_uid | `CREATE INDEX ix_commesse_attivita_sorgente_uid ON vendite.commesse_attivita USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_uid IS NOT NULL)` |
| pk_commesse_attivita | `CREATE UNIQUE INDEX pk_commesse_attivita ON vendite.commesse_attivita USING btree (id)` |
| uq_commesse_attivita_commessa_segment | `CREATE UNIQUE INDEX uq_commesse_attivita_commessa_segment ON vendite.commesse_attivita USING btree (commessa_id, segment_key)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_attivita_a10_area_geografica_fatturazione_r_4e9bb4 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_commesse_attivita_a10_area_geografica_fatturazione_r_4e9bb4 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_commesse_attivita_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_commesse_attivita_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_commesse_attivita_a10_causali_onere_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_onere', 'attivo', 'causale_onere_id', 'id')` |
| trg_commesse_attivita_a10_causali_onere_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_onere', 'attivo', 'causale_onere_id', 'id')` |
| trg_commesse_attivita_a10_guard_contratto_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_contratto()` |
| trg_commesse_attivita_a10_guard_contratto_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_contratto()` |
| trg_commesse_attivita_a10_guard_listino_riga_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_listino_riga()` |
| trg_commesse_attivita_a10_guard_listino_riga_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_listino_riga()` |
| trg_commesse_attivita_a10_guard_prezzo_rettifica_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_guard_prezzo_rettifica()` |
| trg_commesse_attivita_a10_guard_quantita_immutabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_guard_quantita_immutabile()` |
| trg_commesse_attivita_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_commesse_attivita_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_commesse_attivita_a10_guard_sorgente_segment_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_guard_sorgente_segment()` |
| trg_commesse_attivita_a10_guard_sorgente_segment_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_guard_sorgente_segment()` |
| trg_commesse_attivita_a10_guard_tipo_doc_emittibile_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile()` |
| trg_commesse_attivita_a10_guard_tipo_doc_emittibile_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile()` |
| trg_commesse_attivita_a10_listini_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_righe', 'attivo', 'listino_riga_id', 'id')` |
| trg_commesse_attivita_a10_listini_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_righe', 'attivo', 'listino_riga_id', 'id')` |
| trg_commesse_attivita_a10_listini_versioni_require_attiv_5d6a8d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_commesse_attivita_a10_listini_versioni_require_attiv_5d6a8d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_commesse_attivita_a10_nature_doc_fiscale_require_att_626b7e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_commesse_attivita_a10_nature_doc_fiscale_require_att_626b7e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_commesse_attivita_a10_onere_articolo_non_obsoleto_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('catalogo', 'articoli', 'obsoleto_dal', 'articolo_id', 'id', 'sorgente_tipo_id')` |
| trg_commesse_attivita_a10_onere_articolo_non_obsoleto_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('catalogo', 'articoli', 'obsoleto_dal', 'articolo_id', 'id', 'sorgente_tipo_id')` |
| trg_commesse_attivita_a10_promo_articoli_require_attivo__12aecc | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'promo_articoli', 'attivo', 'promo_id', 'id')` |
| trg_commesse_attivita_a10_promo_articoli_require_attivo__12aecc | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'promo_articoli', 'attivo', 'promo_id', 'id')` |
| trg_commesse_attivita_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_commesse_attivita_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_commesse_attivita_a10_tipi_doc_fiscale_require_attiv_89561d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_commesse_attivita_a10_tipi_doc_fiscale_require_attiv_89561d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_commesse_attivita_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_commesse_attivita_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_commesse_attivita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_attivita_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_attivita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_attivita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_attivita_z90_proietta_stato_preventivo_ins_dlt | AFTER | DELETE | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_proietta_stato_preventivo()` |
| trg_commesse_attivita_z90_proietta_stato_preventivo_ins_dlt | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_proietta_stato_preventivo()` |
| trg_commesse_attivita_z90_proietta_stato_preventivo_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_attivita_proietta_stato_preventivo()` |
| trg_commesse_attivita_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_attivita_id')` |
| trg_commesse_attivita_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_attivita_id')` |
| trg_vendite_commesse_attivita_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
