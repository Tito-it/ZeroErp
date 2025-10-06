# 📚 Tabella `inventari_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| inventario_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| qta_contata | numeric | NO |  |
| qta_sistema | numeric | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| ubicazione_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_inventario_righe_qta_contata_non_neg |  |
| FOREIGN KEY | fk_mag_inventari_righe_ubicazione | ubicazione_id |
| FOREIGN KEY | fk_mag_inventario_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_inventario_righe_testata | inventario_id |
| PRIMARY KEY | pk_mag_invetario_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_inventari_righe_ubicazione | `CREATE INDEX ix_mag_inventari_righe_ubicazione ON magazzino.inventari_righe USING btree (ubicazione_id)` |
| ix_mag_invetario_r_articolo | `CREATE INDEX ix_mag_invetario_r_articolo ON magazzino.inventari_righe USING btree (articolo_id)` |
| ix_mag_invetario_r_lotto_upper | `CREATE INDEX ix_mag_invetario_r_lotto_upper ON magazzino.inventari_righe USING btree (upper((lotto)::text))` |
| ix_mag_invetario_r_seriale_upper | `CREATE INDEX ix_mag_invetario_r_seriale_upper ON magazzino.inventari_righe USING btree (upper((seriale)::text))` |
| pk_mag_invetario_righe | `CREATE UNIQUE INDEX pk_mag_invetario_righe ON magazzino.inventari_righe USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
