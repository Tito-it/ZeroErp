{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili.md" %}
# 📚 Tabella `attivita_fatturabili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| billing_account_id | bigint | YES |  |
| istanza_utility_id | bigint | NO |  |
| data_attivita | date | NO |  |
| quantita | numeric | NO |  |
| competenza_mese | date | NO |  |
| approvato | boolean | YES | false |
| fatturato | boolean | YES | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| sorgente_riga | bigint | YES | 0 |
| posticipa_al | date | YES |  |
| sospesa | boolean | YES | false |
| exclude_reason | character varying | YES |  |
| lock_in_fatturazione | boolean | YES | false |
| lock_batch_id | uuid | YES |  |
| fattura_riga_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| uom_id | bigint | YES |  |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |
| valuta_id | integer | YES |  |
| prezzo_unitario | numeric | YES |  |
| lotto_attivita_id | bigint | YES |  |
| attivita_consumi_id | bigint | YES |  |
| uid | uuid | NO | uuidv7() |
| tipo_doc_fiscale_id | bigint | YES |  |
| competenza_dal | date | NO |  |
| competenza_al | date | NO |  |
| area_geografica_id | bigint | YES |  |
| stato_esecuzione | character varying | YES |  |
| prezzo_bloccato | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_competenza_dal_al |  |
| CHECK | chk_attivita_competenza_mese_primo |  |
| CHECK | chk_attivita_fatt_stato_esecuzione |  |
| FOREIGN KEY | fk_attivita_fatturabili_area_geografica | area_geografica_id |
| FOREIGN KEY | fk_attivita_fatturabili_articoli | articolo_id |
| FOREIGN KEY | fk_attivita_fatturabili_attivita_consumi | attivita_consumi_id |
| FOREIGN KEY | fk_attivita_fatturabili_attivita_lotto | lotto_attivita_id |
| FOREIGN KEY | fk_attivita_fatturabili_billing_account | billing_account_id |
| FOREIGN KEY | fk_attivita_fatturabili_istanze_utilities | istanza_utility_id |
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
| idx_att_fatt_lotto_stato_exec | `CREATE INDEX idx_att_fatt_lotto_stato_exec ON vendite.attivita_fatturabili USING btree (lotto_attivita_id, stato_esecuzione)` |
| ix_attivita_articolo_flags | `CREATE INDEX ix_attivita_articolo_flags ON vendite.attivita_fatturabili USING btree (articolo_id, approvato, fatturato)` |
| ix_attivita_billing_competenza | `CREATE INDEX ix_attivita_billing_competenza ON vendite.attivita_fatturabili USING btree (billing_account_id, competenza_mese)` |
| ix_attivita_fatturabili_fattura_riga_id | `CREATE INDEX ix_attivita_fatturabili_fattura_riga_id ON vendite.attivita_fatturabili USING btree (fattura_riga_id)` |
| ix_attivita_fatturabili_lock | `CREATE INDEX ix_attivita_fatturabili_lock ON vendite.attivita_fatturabili USING btree (lock_in_fatturazione, lock_batch_id)` |
| ix_attivita_fatturabili_posticipa_sospesa | `CREATE INDEX ix_attivita_fatturabili_posticipa_sospesa ON vendite.attivita_fatturabili USING btree (posticipa_al, sospesa)` |
| ix_attivita_istanza_data | `CREATE INDEX ix_attivita_istanza_data ON vendite.attivita_fatturabili USING btree (istanza_utility_id, data_attivita)` |
| pk_attivita_fatturabili | `CREATE UNIQUE INDEX pk_attivita_fatturabili ON vendite.attivita_fatturabili USING btree (id)` |
| uq_attivita_fatturabili_uid | `CREATE UNIQUE INDEX uq_attivita_fatturabili_uid ON vendite.attivita_fatturabili USING btree (uid)` |
| uq_attivita_fatturabili_v_sorgente_fk | `CREATE UNIQUE INDEX uq_attivita_fatturabili_v_sorgente_fk ON vendite.attivita_fatturabili USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_fatturabili_a10_area_geografica_fatturazion_dce856 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id')` |
| trg_attivita_fatturabili_a10_area_geografica_fatturazion_dce856 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id')` |
| trg_attivita_fatturabili_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_attivita_fatturabili_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_attivita_fatturabili_a10_guard_ba_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_attivita_fatturabili_a10_guard_fatturato_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()` |
| trg_attivita_fatturabili_a10_guard_fatturato_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fatturato()` |
| trg_attivita_fatturabili_a10_guard_fonte_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa()` |
| trg_attivita_fatturabili_a10_guard_fonte_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa()` |
| trg_attivita_fatturabili_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_attivita_fatturabili_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_attivita_fatturabili_a10_tipi_doc_fiscale_require_at_ecad50 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id')` |
| trg_attivita_fatturabili_a10_tipi_doc_fiscale_require_at_ecad50 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_a573b4 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_a573b4 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_d45cbd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id')` |
| trg_attivita_fatturabili_a10_unita_misura_require_attivo_d45cbd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id')` |
| trg_attivita_fatturabili_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_normalize()` |
| trg_attivita_fatturabili_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_normalize()` |
| trg_attivita_fatturabili_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_fatturabili_id')` |
| trg_attivita_fatturabili_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_fatturabili_id')` |

---
{% include-markdown "signature-core.md" %}
