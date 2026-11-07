{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili.md" %}
# 📚 Tabella `attivita_fatturabili`

> 📝 **Descrizione**
>
> Registro attività/prestazioni da fatturare (HH, una tantum, manuali). Se competenza_mese è valorizzato (YYYY-MM-01), non fatturare prima di quel mese.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| billing_account_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| data_attivita | date | NO |  |
| quantita | numeric(18,6) | NO |  |
| competenza_mese | date | NO |  |
| approvato | boolean | YES | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| sorgente_riga | bigint | YES | 0 |
| posticipa_al | date | YES |  |
| sospesa | boolean | YES | false |
| exclude_reason | character varying(200) | YES |  |
| lock_in_fatturazione | boolean | YES | false |
| lock_batch_id | uuid | YES |  |
| fattura_riga_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| uom_id | bigint | YES |  |
| qta_operativa | numeric(18,6) | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric(18,6) | NO | 1 |
| valuta_id | integer | YES |  |
| prezzo_unitario | numeric(20,8) | YES |  |
| attivita_consumi_id | bigint | YES |  |
| uid | uuid | NO | uuidv7() |
| tipo_doc_fiscale_id | bigint | YES |  |
| competenza_dal | date | NO |  |
| competenza_al | date | NO |  |
| area_geografica_id | bigint | YES |  |
| stato_esecuzione | character varying(16) | YES |  |
| prezzo_bloccato | boolean | NO | false |
| commessa_id | bigint | NO |  |
| commessa_attivita_id | bigint | NO |  |
| sorgente_origine_tipo_id | bigint | YES |  |
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
| natura_doc_id | bigint | NO | config.fn_get_natura_doc_fiscale_id('FATTURA'::character varying) |
| fattura_riga_rettificata_id | bigint | YES |  |
| fatturato | boolean | NO |  |
| emit_batch_id | uuid | YES |  |
| natura_dal_segno | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_competenza_dal_al |  |
| CHECK | chk_attivita_competenza_mese_primo |  |
| CHECK | chk_attivita_fatt_stato_esecuzione |  |
| CHECK | chk_attivita_fatturabili_factor_to_base_finito |  |
| CHECK | chk_attivita_fatturabili_origine_prezzo |  |
| CHECK | chk_attivita_fatturabili_prezzo_base_snapshot_finito |  |
| CHECK | chk_attivita_fatturabili_prezzo_unitario_finito |  |
| CHECK | chk_attivita_fatturabili_qta_operativa_finito |  |
| CHECK | chk_attivita_fatturabili_quantita_finito |  |
| CHECK | chk_attivita_fatturabili_rettificata_e_rettifica |  |
| CHECK | chk_attivita_fatturabili_tipo_movimento |  |
| CHECK | chk_attivita_fatturabili_tipo_variazione_applicata |  |
| CHECK | chk_attivita_fatturabili_valore_variazione_applicata_finito |  |
| FOREIGN KEY | attivita_fatturabili_listino_riga_id_fkey | listino_riga_id |
| FOREIGN KEY | fk_attivita_fatturabili_area_geografica | area_geografica_id |
| FOREIGN KEY | fk_attivita_fatturabili_articoli | articolo_id |
| FOREIGN KEY | fk_attivita_fatturabili_attivita_consumi | attivita_consumi_id |
| FOREIGN KEY | fk_attivita_fatturabili_billing_account | billing_account_id |
| FOREIGN KEY | fk_attivita_fatturabili_categoria_cliente_snapshot | categoria_cliente_id_snapshot |
| FOREIGN KEY | fk_attivita_fatturabili_classe_utenza_snapshot | classe_utenza_id_snapshot |
| FOREIGN KEY | fk_attivita_fatturabili_commessa | commessa_id |
| FOREIGN KEY | fk_attivita_fatturabili_commessa_attivita | commessa_attivita_id |
| FOREIGN KEY | fk_attivita_fatturabili_contratto | contratto_id |
| FOREIGN KEY | fk_attivita_fatturabili_fattura_riga | fattura_riga_id |
| FOREIGN KEY | fk_attivita_fatturabili_fattura_riga_rettificata | fattura_riga_rettificata_id |
| FOREIGN KEY | fk_attivita_fatturabili_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_attivita_fatturabili_natura_doc | natura_doc_id |
| FOREIGN KEY | fk_attivita_fatturabili_promo | promo_id |
| FOREIGN KEY | fk_attivita_fatturabili_sorgente_origine_tipo | sorgente_origine_tipo_id |
| FOREIGN KEY | fk_attivita_fatturabili_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_attivita_fatturabili_tipo_doc_fiscale | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_attivita_fatturabili_uom_id | uom_id |
| FOREIGN KEY | fk_attivita_fatturabili_uom_operativa_id | uom_operativa_id |
| FOREIGN KEY | fk_attivita_fatturabili_valuta | valuta_id |
| PRIMARY KEY | pk_attivita_fatturabili | id |
| UNIQUE | uq_attivita_fatturabili_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_attivita_articolo_flags | `CREATE INDEX ix_attivita_articolo_flags ON vendite.attivita_fatturabili USING btree (articolo_id, approvato, fatturato)` |
| ix_attivita_billing_competenza | `CREATE INDEX ix_attivita_billing_competenza ON vendite.attivita_fatturabili USING btree (billing_account_id, competenza_mese)` |
| ix_attivita_fatturabili_commessa_id | `CREATE INDEX ix_attivita_fatturabili_commessa_id ON vendite.attivita_fatturabili USING btree (commessa_id)` |
| ix_attivita_fatturabili_competenza_mese | `CREATE INDEX ix_attivita_fatturabili_competenza_mese ON vendite.attivita_fatturabili USING btree (competenza_mese)` |
| ix_attivita_fatturabili_fattura_riga_id | `CREATE INDEX ix_attivita_fatturabili_fattura_riga_id ON vendite.attivita_fatturabili USING btree (fattura_riga_id)` |
| ix_attivita_fatturabili_fattura_riga_rettificata_id | `CREATE INDEX ix_attivita_fatturabili_fattura_riga_rettificata_id ON vendite.attivita_fatturabili USING btree (fattura_riga_rettificata_id) WHERE (fattura_riga_rettificata_id IS NOT NULL)` |
| ix_attivita_fatturabili_listino_riga_id | `CREATE INDEX ix_attivita_fatturabili_listino_riga_id ON vendite.attivita_fatturabili USING btree (listino_riga_id) WHERE (listino_riga_id IS NOT NULL)` |
| ix_attivita_fatturabili_lock | `CREATE INDEX ix_attivita_fatturabili_lock ON vendite.attivita_fatturabili USING btree (lock_in_fatturazione, lock_batch_id)` |
| ix_attivita_fatturabili_origine_prezzo | `CREATE INDEX ix_attivita_fatturabili_origine_prezzo ON vendite.attivita_fatturabili USING btree (origine_prezzo)` |
| ix_attivita_fatturabili_posticipa_sospesa | `CREATE INDEX ix_attivita_fatturabili_posticipa_sospesa ON vendite.attivita_fatturabili USING btree (posticipa_al, sospesa)` |
| ix_attivita_istanza_data | `CREATE INDEX ix_attivita_istanza_data ON vendite.attivita_fatturabili USING btree (istanza_utility_id, data_attivita)` |
| pk_attivita_fatturabili | `CREATE UNIQUE INDEX pk_attivita_fatturabili ON vendite.attivita_fatturabili USING btree (id)` |
| uq_attivita_fatturabili_commessa_attivita | `CREATE UNIQUE INDEX uq_attivita_fatturabili_commessa_attivita ON vendite.attivita_fatturabili USING btree (commessa_attivita_id)` |
| uq_attivita_fatturabili_uid | `CREATE UNIQUE INDEX uq_attivita_fatturabili_uid ON vendite.attivita_fatturabili USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_fatturabili_a10_area_geografica_fatturazion_dce856 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_attivita_fatturabili_a10_area_geografica_fatturazion_dce856 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_attivita_fatturabili_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_attivita_fatturabili_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_attivita_fatturabili_a10_guard_commessa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_commessa()` |
| trg_attivita_fatturabili_a10_guard_commessa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_commessa()` |
| trg_attivita_fatturabili_a10_guard_contratto_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_contratto()` |
| trg_attivita_fatturabili_a10_guard_contratto_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_contratto()` |
| trg_attivita_fatturabili_a10_guard_fatturato_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()` |
| trg_attivita_fatturabili_a10_guard_fatturato_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()` |
| trg_attivita_fatturabili_a10_guard_listino_riga_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_listino_riga()` |
| trg_attivita_fatturabili_a10_guard_listino_riga_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_guard_listino_riga()` |
| trg_attivita_fatturabili_a10_guard_quantita_immutabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile()` |
| trg_attivita_fatturabili_a10_listini_righe_require_attiv_48a055 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_righe', 'attivo', 'listino_riga_id', 'id')` |
| trg_attivita_fatturabili_a10_listini_righe_require_attiv_48a055 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_righe', 'attivo', 'listino_riga_id', 'id')` |
| trg_attivita_fatturabili_a10_nature_doc_fiscale_require__13c8b1 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_attivita_fatturabili_a10_nature_doc_fiscale_require__13c8b1 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_attivita_fatturabili_a10_promo_articoli_require_atti_1e76a9 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'promo_articoli', 'attivo', 'promo_id', 'id')` |
| trg_attivita_fatturabili_a10_promo_articoli_require_atti_1e76a9 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'promo_articoli', 'attivo', 'promo_id', 'id')` |
| trg_attivita_fatturabili_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_origine_tipo_id', 'id')` |
| trg_attivita_fatturabili_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_origine_tipo_id', 'id')` |
| trg_attivita_fatturabili_a10_tipi_doc_fiscale_require_at_ecad50 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_attivita_fatturabili_a10_tipi_doc_fiscale_require_at_ecad50 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_a573b4 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_a573b4 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_d45cbd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_d45cbd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_attivita_fatturabili_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_normalize()` |
| trg_attivita_fatturabili_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_normalize()` |
| trg_attivita_fatturabili_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_fatturabili_id')` |
| trg_attivita_fatturabili_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_fatturabili_id')` |
| trg_vendite_attivita_fatturabili_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
