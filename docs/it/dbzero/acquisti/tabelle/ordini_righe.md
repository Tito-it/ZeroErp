# 📚 Tabella `ordini_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | NO |  |
| uom_id | bigint | YES |  |
| qta | numeric | NO |  |
| prezzo_unitario | numeric | NO |  |
| sconto_perc | numeric | YES |  |
| iva_id | integer | YES |  |
| stato_doc_ordine_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_riga | bigint | YES | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| hash_contenuto | character varying | YES |  |
| sorgente_uid | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_ao_r_przz_pos |  |
| CHECK | chk_ordini_ao_r_qta_pos |  |
| CHECK | chk_ordini_ao_r_sconto_perc |  |
| FOREIGN KEY | fk_ao_r_articolo | articolo_id |
| FOREIGN KEY | fk_ao_r_iva | iva_id |
| FOREIGN KEY | fk_ao_r_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ao_r_stato_doc_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ao_r_testata | ordine_id |
| FOREIGN KEY | fk_ao_r_uom | uom_id |
| PRIMARY KEY | pk_ao_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ao_r_articolo | `CREATE INDEX ix_ao_r_articolo ON acquisti.ordini_righe USING btree (articolo_id)` |
| ix_ao_r_stato_doc | `CREATE INDEX ix_ao_r_stato_doc ON acquisti.ordini_righe USING btree (stato_doc_ordine_id)` |
| ix_ao_r_testata | `CREATE INDEX ix_ao_r_testata ON acquisti.ordini_righe USING btree (ordine_id)` |
| pk_ao_righe | `CREATE UNIQUE INDEX pk_ao_righe ON acquisti.ordini_righe USING btree (id)` |
| uq_ao_r_riga_nr | `CREATE UNIQUE INDEX uq_ao_r_riga_nr ON acquisti.ordini_righe USING btree (ordine_id, riga_nr)` |
| uq_ordini_righe_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_righe_v_sorgente_fk ON acquisti.ordini_righe USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

---
{% include-markdown "signature-core.md" %}
