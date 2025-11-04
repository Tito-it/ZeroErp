# 📚 Tabella `ordini_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | NO |  |
| qta | numeric | NO |  |
| prezzo_unitario | numeric | NO |  |
| sconto_perc | numeric | YES |  |
| iva_id | integer | YES |  |
| iva_perc | numeric | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_riga | bigint | YES | 0 |
| stato_doc_ordine_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | check_ordini_righe_qta_operativa_pos |  |
| CHECK | chk_ordini_v_r_prezzo_pos |  |
| CHECK | chk_ordini_v_r_qta_pos |  |
| CHECK | chk_ordini_v_r_sconto_perc |  |
| FOREIGN KEY | fk_ordini_vendita_r_uom_operativa | uom_operativa_id |
| FOREIGN KEY | fk_ordrig_articolo | articolo_id |
| FOREIGN KEY | fk_ordrig_iva | iva_id |
| FOREIGN KEY | fk_ordrig_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ordrig_stato_doc_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordrig_testata | ordine_id |
| PRIMARY KEY | pk_ordrig | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordrig_articolo | `CREATE INDEX ix_ordrig_articolo ON vendite.ordini_righe USING btree (articolo_id)` |
| ix_ordrig_stato_doc | `CREATE INDEX ix_ordrig_stato_doc ON vendite.ordini_righe USING btree (stato_doc_ordine_id)` |
| ix_ordrig_testata | `CREATE INDEX ix_ordrig_testata ON vendite.ordini_righe USING btree (ordine_id)` |
| pk_ordrig | `CREATE UNIQUE INDEX pk_ordrig ON vendite.ordini_righe USING btree (id)` |
| uq_ordini_righe_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_righe_v_sorgente_fk ON vendite.ordini_righe USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |
| uq_ordrig_riga_nr | `CREATE UNIQUE INDEX uq_ordrig_riga_nr ON vendite.ordini_righe USING btree (ordine_id, riga_nr)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_dlt_block | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_a10_dlt_block_ordrig_ddtrig()` |

---
{% include-markdown "signature-core.md" %}
