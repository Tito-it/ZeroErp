{% include-markdown "it/dbzero/vendite/manual/fatture_righe.md" %}
# 📚 Tabella `fatture_righe`

> 📝 **Descrizione**
>
> Righe fattura: contenuti, IVA snapshot, attribuzione al child BA, importi congelati, sorgente.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | YES |  |
| descrizione | character varying(150) | NO |  |
| uom_id | bigint | YES |  |
| qta | numeric(18,6) | NO |  |
| prezzo_unitario | numeric(18,6) | NO |  |
| sconto_percentuale | numeric(5,2) | YES | 0 |
| iva_id | integer | YES |  |
| esigibilita | character(1) | YES |  |
| split_payment | boolean | YES |  |
| dest_billing_account_id | bigint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_riga | bigint | YES |  |
| iva_natura | character varying(10) | YES |  |
| sorgente_uid | uuid | YES |  |
| imponibile_riga | numeric(18,6) | NO |  |
| kit_key | text | YES |  |
| kit_esposizione | character varying(40) | YES |  |
| kit_articolo_padre_id | uuid | YES |  |
| kit_descrizione_padre | character varying(150) | YES |  |
| riga_rettificata_id | bigint | YES |  |
| aliquota_iva | numeric(5,2) | YES |  |
| fattura_atto_id | bigint | YES |  |
| riga_capofila_id | bigint | YES |  |
| competenza_dal | date | NO |  |
| competenza_al | date | NO |  |
| kit_qta | numeric(18,6) | YES |  |
| kit_uom_id | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_righe_aliquota_iva_finito |  |
| CHECK | chk_fatture_righe_capofila_non_se_stessa |  |
| CHECK | chk_fatture_righe_competenza_dal_al |  |
| CHECK | chk_fatture_righe_esigibilita |  |
| CHECK | chk_fatture_righe_imponibile_riga_finito |  |
| CHECK | chk_fatture_righe_kit_articolo |  |
| CHECK | chk_fatture_righe_kit_coerente |  |
| CHECK | chk_fatture_righe_kit_qta_finito |  |
| CHECK | chk_fatture_righe_prezzo_unitario_finito |  |
| CHECK | chk_fatture_righe_qta_finito |  |
| CHECK | chk_fatture_righe_rettificata_non_se_stessa |  |
| CHECK | chk_fatture_righe_sconto |  |
| CHECK | chk_fatture_righe_sconto_percentuale_finito |  |
| CHECK | chk_fatture_righe_sorgente_forma |  |
| FOREIGN KEY | fk_fatture_righe_art | articolo_id |
| FOREIGN KEY | fk_fatture_righe_ba_dest | dest_billing_account_id |
| FOREIGN KEY | fk_fatture_righe_esposizioni_componente | kit_esposizione |
| FOREIGN KEY | fk_fatture_righe_fat | fattura_id |
| FOREIGN KEY | fk_fatture_righe_fattura_atto | fattura_atto_id, fattura_id |
| FOREIGN KEY | fk_fatture_righe_iva | iva_id |
| FOREIGN KEY | fk_fatture_righe_kit_articolo_padre | kit_articolo_padre_id |
| FOREIGN KEY | fk_fatture_righe_kit_uom | kit_uom_id |
| FOREIGN KEY | fk_fatture_righe_riga_capofila | riga_capofila_id, fattura_id |
| FOREIGN KEY | fk_fatture_righe_riga_rettificata | riga_rettificata_id |
| FOREIGN KEY | fk_fatture_righe_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_fatture_righe_uom | uom_id |
| PRIMARY KEY | pk_fatture_righe | id |
| UNIQUE | uq_fatture_righe_id_fattura | id, fattura_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_righe_fattura_atto_id | `CREATE INDEX ix_fatture_righe_fattura_atto_id ON vendite.fatture_righe USING btree (fattura_atto_id, fattura_id) WHERE (fattura_atto_id IS NOT NULL)` |
| ix_fatture_righe_riga_capofila_id | `CREATE INDEX ix_fatture_righe_riga_capofila_id ON vendite.fatture_righe USING btree (riga_capofila_id, fattura_id) WHERE (riga_capofila_id IS NOT NULL)` |
| ix_fatture_righe_riga_rettificata_id | `CREATE INDEX ix_fatture_righe_riga_rettificata_id ON vendite.fatture_righe USING btree (riga_rettificata_id) WHERE (riga_rettificata_id IS NOT NULL)` |
| ix_fatture_righe_sorgente_id | `CREATE INDEX ix_fatture_righe_sorgente_id ON vendite.fatture_righe USING btree (sorgente_tipo_id, sorgente_id) WHERE (sorgente_id IS NOT NULL)` |
| ix_fatture_righe_sorgente_riga | `CREATE INDEX ix_fatture_righe_sorgente_riga ON vendite.fatture_righe USING btree (sorgente_tipo_id, sorgente_riga) WHERE (sorgente_riga IS NOT NULL)` |
| ix_fatture_righe_sorgente_uid | `CREATE INDEX ix_fatture_righe_sorgente_uid ON vendite.fatture_righe USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_uid IS NOT NULL)` |
| ix_vendite_fatture_righe_dest_billing_account_id | `CREATE INDEX ix_vendite_fatture_righe_dest_billing_account_id ON vendite.fatture_righe USING btree (dest_billing_account_id)` |
| ix_vendite_fatture_righe_iva_id | `CREATE INDEX ix_vendite_fatture_righe_iva_id ON vendite.fatture_righe USING btree (iva_id)` |
| pk_fatture_righe | `CREATE UNIQUE INDEX pk_fatture_righe ON vendite.fatture_righe USING btree (id)` |
| uq_fatture_righe_id_fattura | `CREATE UNIQUE INDEX uq_fatture_righe_id_fattura ON vendite.fatture_righe USING btree (id, fattura_id)` |
| uq_fatture_righe_riga_nr | `CREATE UNIQUE INDEX uq_fatture_righe_riga_nr ON vendite.fatture_righe USING btree (fattura_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_fatture_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id', 'E_FATTURA_RIGA_CONGELATA')` |
| trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id', 'E_FATTURA_RIGA_CONGELATA')` |
| trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id', 'E_FATTURA_RIGA_CONGELATA')` |
| trg_fatture_righe_a10_guard_riga_capofila_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_guard_riga_capofila()` |
| trg_fatture_righe_a10_guard_riga_capofila_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_guard_riga_capofila()` |
| trg_fatture_righe_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_fatture_righe_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_fatture_righe_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_fatture_righe_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_fatture_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_fatture_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_fatture_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_fatture_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_fatture_righe_a20_importo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_importo()` |
| trg_fatture_righe_a20_importo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_importo()` |
| trg_fatture_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_righe_guard_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_guard_normalize()` |
| trg_fatture_righe_guard_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_guard_normalize()` |
| trg_fatture_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_righe_id')` |
| trg_fatture_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_righe_id')` |
| trg_vendite_fatture_righe_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
