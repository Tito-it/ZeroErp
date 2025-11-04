{% include-markdown "it/dbzero/vendite/manual/ddt_righe.md" %}
# 📚 Tabella `ddt_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ddt_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | NO |  |
| qta | numeric | NO |  |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | k_ddt_righe_qta_operativa_pos |  |
| CHECK | k_ddt_righe_qta_pos |  |
| FOREIGN KEY | fk_ddt_vendita_r_articolo | articolo_id |
| FOREIGN KEY | fk_ddt_vendita_r_testata | ddt_id |
| FOREIGN KEY | fk_ddt_vendita_r_uom_operativa | uom_operativa_id |
| PRIMARY KEY | pk_ddtvr | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ddt_vendita_r_articolo | `CREATE INDEX ix_ddt_vendita_r_articolo ON vendite.ddt_righe USING btree (articolo_id)` |
| pk_ddtvr | `CREATE UNIQUE INDEX pk_ddtvr ON vendite.ddt_righe USING btree (id)` |
| uq_ddt_vendita_r_riga_nr | `CREATE UNIQUE INDEX uq_ddt_vendita_r_riga_nr ON vendite.ddt_righe USING btree (ddt_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_dlt_block_ddt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_a10_dlt_block_ordrig_ddtrig()` |
| trg_a10_ins_upd_ddt_righe_qta_from_operativa | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa()` |
| trg_a10_ins_upd_ddt_righe_qta_from_operativa | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa()` |

---
{% include-markdown "signature-core.md" %}
