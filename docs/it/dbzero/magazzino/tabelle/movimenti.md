# 📚 Tabella `movimenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | NO |  |
| magazzino_id_dest | bigint | YES |  |
| uom_id | bigint | YES |  |
| qta | numeric | NO |  |
| costo_unitario | numeric | YES |  |
| data_mov | timestamp with time zone | NO | now() |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| causale_id | bigint | NO |  |
| sorgente_schema | character varying | YES |  |
| sorgente_tabella | character varying | YES |  |
| sorgente_id | bigint | YES |  |
| sorgente_riga_id | bigint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |
| transfer_uid | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_movimenti_qta_non_zero |  |
| FOREIGN KEY | fk_mag_movimenti_articolo | articolo_id |
| FOREIGN KEY | fk_mag_movimenti_causale | causale_id |
| FOREIGN KEY | fk_mag_movimenti_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_movimenti_magazzino_dest | magazzino_id_dest |
| FOREIGN KEY | fk_mag_movimenti_uom | uom_id |
| PRIMARY KEY | pk_mag_movimenti | id |
| UNIQUE | uq_mag_movimenti_sorgente | sorgente_schema, sorgente_tabella, sorgente_id, sorgente_riga_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_mov_transfer_uid | `CREATE INDEX ix_mag_mov_transfer_uid ON magazzino.movimenti USING btree (transfer_uid)` |
| ix_mag_movimenti_articolo | `CREATE INDEX ix_mag_movimenti_articolo ON magazzino.movimenti USING btree (articolo_id)` |
| ix_mag_movimenti_causale | `CREATE INDEX ix_mag_movimenti_causale ON magazzino.movimenti USING btree (causale_id)` |
| ix_mag_movimenti_data | `CREATE INDEX ix_mag_movimenti_data ON magazzino.movimenti USING btree (data_mov)` |
| ix_mag_movimenti_lotto_upper | `CREATE INDEX ix_mag_movimenti_lotto_upper ON magazzino.movimenti USING btree (upper((lotto)::text))` |
| ix_mag_movimenti_magazzino | `CREATE INDEX ix_mag_movimenti_magazzino ON magazzino.movimenti USING btree (magazzino_id)` |
| ix_mag_movimenti_magazzino_dest | `CREATE INDEX ix_mag_movimenti_magazzino_dest ON magazzino.movimenti USING btree (magazzino_id_dest)` |
| ix_mag_movimenti_seriale_upper | `CREATE INDEX ix_mag_movimenti_seriale_upper ON magazzino.movimenti USING btree (upper((seriale)::text))` |
| ix_mag_movimenti_sorgente | `CREATE INDEX ix_mag_movimenti_sorgente ON magazzino.movimenti USING btree (sorgente_schema, sorgente_tabella, sorgente_id, sorgente_riga_id)` |
| pk_mag_movimenti | `CREATE UNIQUE INDEX pk_mag_movimenti ON magazzino.movimenti USING btree (id)` |
| uq_mag_movimenti_sorgente | `CREATE UNIQUE INDEX uq_mag_movimenti_sorgente ON magazzino.movimenti USING btree (sorgente_schema, sorgente_tabella, sorgente_id, sorgente_riga_id)` |

---
{% include-markdown "signature-core.md" %}
