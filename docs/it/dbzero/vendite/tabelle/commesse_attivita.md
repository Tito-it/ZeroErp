{% include-markdown "it/dbzero/vendite/manual/commesse_attivita.md" %}
# 📚 Tabella `commesse_attivita`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| commessa_id | bigint | NO |  |
| segment_key | character varying | NO |  |
| articolo_id | uuid | NO |  |
| istanza_utility_id | bigint | NO |  |
| data_attivita | date | NO |  |
| uom_id | bigint | NO |  |
| quantita | numeric | NO |  |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |
| competenza_mese | date | NO |  |
| competenza_dal | date | NO |  |
| competenza_al | date | NO |  |
| posticipa_al | date | YES |  |
| tipo_doc_fiscale_id | bigint | YES |  |
| valuta_id | integer | YES |  |
| area_geografica_id | bigint | YES |  |
| listino_versione_id | bigint | YES |  |
| prezzo_snapshot | numeric | NO |  |
| prezzo_bloccato | boolean | NO | false |
| pricing_mode | character varying | NO | 'FIXED'::character varying |
| prezzo_da_riallineare | boolean | NO | false |
| stato_approvazione | character varying | NO | 'BOZZA'::character varying |
| stato_emissione | character varying | NO | 'NON_EMESSA'::character varying |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | text | YES |  |
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
| CHECK | chk_commesse_attivita_comp_mese_primo |  |
| CHECK | chk_commesse_attivita_comp_range |  |
| CHECK | chk_commesse_attivita_factor_to_base |  |
| CHECK | chk_commesse_attivita_posticipa |  |
| CHECK | chk_commesse_attivita_prezzo |  |
| CHECK | chk_commesse_attivita_pricing_mode |  |
| CHECK | chk_commesse_attivita_sorgente_pair |  |
| CHECK | chk_commesse_attivita_stato_approvazione |  |
| CHECK | chk_commesse_attivita_stato_emissione |  |
| FOREIGN KEY | fk_commesse_attivita_area_geo | area_geografica_id |
| FOREIGN KEY | fk_commesse_attivita_articolo | articolo_id |
| FOREIGN KEY | fk_commesse_attivita_commessa | commessa_id |
| FOREIGN KEY | fk_commesse_attivita_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_commesse_attivita_listino_versione | listino_versione_id |
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
| pk_commesse_attivita | `CREATE UNIQUE INDEX pk_commesse_attivita ON vendite.commesse_attivita USING btree (id)` |
| uq_commesse_attivita_commessa_segment | `CREATE UNIQUE INDEX uq_commesse_attivita_commessa_segment ON vendite.commesse_attivita USING btree (commessa_id, segment_key)` |
| uq_commesse_attivita_src_uid_partial | `CREATE UNIQUE INDEX uq_commesse_attivita_src_uid_partial ON vendite.commesse_attivita USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_attivita_a10_area_geografica_fatturazione_r_4e9bb4 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id')` |
| trg_commesse_attivita_a10_area_geografica_fatturazione_r_4e9bb4 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id')` |
| trg_commesse_attivita_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_commesse_attivita_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_commesse_attivita_a10_listini_versioni_require_attiv_5d6a8d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id')` |
| trg_commesse_attivita_a10_listini_versioni_require_attiv_5d6a8d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id')` |
| trg_commesse_attivita_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_commesse_attivita_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_commesse_attivita_a10_tipi_doc_fiscale_require_attiv_89561d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id')` |
| trg_commesse_attivita_a10_tipi_doc_fiscale_require_attiv_89561d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id')` |
| trg_commesse_attivita_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_commesse_attivita_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_commesse_attivita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_attivita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_attivita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_attivita_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_attivita_id')` |
| trg_commesse_attivita_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_attivita_id')` |

---
{% include-markdown "signature-core.md" %}
