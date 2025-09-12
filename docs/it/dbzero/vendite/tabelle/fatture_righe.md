# 📚 Tabella `fatture_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | YES |  |
| descrizione | character varying | NO |  |
| uom_id | bigint | YES |  |
| qta | numeric | NO |  |
| prezzo_unitario | numeric | NO |  |
| sconto_perc | numeric | YES |  |
| iva_id | integer | YES |  |
| esigibilita | character | YES |  |
| split_payment | boolean | YES |  |
| dest_billing_account_id | integer | YES |  |
| imponibile_riga | numeric | YES |  |
| imposta_riga | numeric | YES |  |
| totale_riga | numeric | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_id | uuid | YES |  |
| sorgente_riga | bigint | YES | 0 |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_righe_sconto_perc |  |
| FOREIGN KEY | fk_fatture_righe_art | articolo_id |
| FOREIGN KEY | fk_fatture_righe_ba_dest | dest_billing_account_id |
| FOREIGN KEY | fk_fatture_righe_fat | fattura_id |
| FOREIGN KEY | fk_fatture_righe_iva | iva_id |
| FOREIGN KEY | fk_fatture_righe_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_fatture_righe_uom | uom_id |
| PRIMARY KEY | pk_fatture_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_righe_ba_dest | `CREATE INDEX ix_fatture_righe_ba_dest ON vendite.fatture_righe USING btree (dest_billing_account_id)` |
| ix_fatture_righe_fattura | `CREATE INDEX ix_fatture_righe_fattura ON vendite.fatture_righe USING btree (fattura_id)` |
| ix_fatture_righe_iva | `CREATE INDEX ix_fatture_righe_iva ON vendite.fatture_righe USING btree (iva_id)` |
| pk_fatture_righe | `CREATE UNIQUE INDEX pk_fatture_righe ON vendite.fatture_righe USING btree (id)` |
| uq_fatture_righe_riga_nr | `CREATE UNIQUE INDEX uq_fatture_righe_riga_nr ON vendite.fatture_righe USING btree (fattura_id, riga_nr)` |
| uq_fatture_righe_sorgente_fk | `CREATE UNIQUE INDEX uq_fatture_righe_sorgente_fk ON vendite.fatture_righe USING btree (sorgente_tipo_id, sorgente_id, sorgente_riga)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_righe_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_righe_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_righe_ins_upd_norm_guard | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_norm_guard()` |
| trg_fatture_righe_ins_upd_norm_guard | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_righe_norm_guard()` |
| trg_upd_fatture_righe_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_fatture_righe_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('fatture_righe_id')` |
| trg_z90_fatture_righe_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('fatture_righe_id')` |

---
{% include-markdown "signature-core.md" %}
