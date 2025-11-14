# 📚 Tabella `reservations`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | YES |  |
| qta | numeric | NO |  |
| stato_reservation | character varying | NO | 'planned'::character varying |
| data_prevista | timestamp with time zone | YES |  |
| doc_schema | character varying | NO |  |
| doc_table | character varying | NO |  |
| doc_id | bigint | NO |  |
| doc_riga_id | bigint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |
| ubicazione_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_res_qta_pos |  |
| CHECK | chk_mag_res_stato |  |
| FOREIGN KEY | fk_mag_reservations_articolo | articolo_id |
| FOREIGN KEY | fk_mag_reservations_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_reservations_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_mag_reservations | id |
| UNIQUE | uq_mag_reservations_docref | doc_riga_id, doc_id, doc_table, doc_schema |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_res_articolo | `CREATE INDEX ix_mag_res_articolo ON magazzino.reservations USING btree (articolo_id)` |
| ix_mag_res_magazzino | `CREATE INDEX ix_mag_res_magazzino ON magazzino.reservations USING btree (magazzino_id)` |
| ix_mag_res_sorgente | `CREATE INDEX ix_mag_res_sorgente ON magazzino.reservations USING btree (doc_schema, doc_table, doc_id, doc_riga_id)` |
| ix_mag_res_stato | `CREATE INDEX ix_mag_res_stato ON magazzino.reservations USING btree (stato_reservation)` |
| ix_mag_reservations_ubicazione | `CREATE INDEX ix_mag_reservations_ubicazione ON magazzino.reservations USING btree (ubicazione_id)` |
| pk_mag_reservations | `CREATE UNIQUE INDEX pk_mag_reservations ON magazzino.reservations USING btree (id)` |
| uq_mag_reservations_docref | `CREATE UNIQUE INDEX uq_mag_reservations_docref ON magazzino.reservations USING btree (doc_schema, doc_table, doc_id, doc_riga_id)` |

---
{% include-markdown "signature-core.md" %}
