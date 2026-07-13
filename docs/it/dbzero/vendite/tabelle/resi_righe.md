# 📚 Tabella `resi_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| reso_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| ddt_riga_id | bigint | NO |  |
| ordine_riga_id | bigint | YES |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | NO |  |
| quantita | numeric | NO |  |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |
| tipo_reso_id | bigint | NO |  |
| motivo | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | k_resi_righe_qta_operativa_pos |  |
| CHECK | k_resi_righe_qta_pos |  |
| FOREIGN KEY | fk_resi_righe_articolo | articolo_id |
| FOREIGN KEY | fk_resi_righe_ddt_riga | ddt_riga_id |
| FOREIGN KEY | fk_resi_righe_ordine_riga | ordine_riga_id |
| FOREIGN KEY | fk_resi_righe_testata | reso_id |
| FOREIGN KEY | fk_resi_righe_tipo_reso | tipo_reso_id |
| FOREIGN KEY | fk_resi_righe_uom_operativa | uom_operativa_id |
| PRIMARY KEY | pk_resi_righe | id |
| UNIQUE | uq_resi_righe_riga_nr | reso_id, riga_nr |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_resi_righe | `CREATE UNIQUE INDEX pk_resi_righe ON vendite.resi_righe USING btree (id)` |
| uq_resi_righe_riga_nr | `CREATE UNIQUE INDEX uq_resi_righe_riga_nr ON vendite.resi_righe USING btree (reso_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_resi_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_resi_righe_a20_guard_quantita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_righe_guard_quantita()` |
| trg_resi_righe_a20_guard_quantita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_righe_guard_quantita()` |

---
{% include-markdown "signature-core.md" %}
