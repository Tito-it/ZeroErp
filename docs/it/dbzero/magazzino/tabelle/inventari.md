# 📚 Tabella `inventari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| data | date | NO | CURRENT_DATE |
| stato_mag_inventario | character varying | NO | 'DRAFT'::character varying |
| magazzino_id | bigint | NO |  |
| descrizione | character varying | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_mag_invetario_stato |  |
| FOREIGN KEY | fk_mag_inventari_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_inventari_sorgenti_tipo | sorgente_tipo_id |
| PRIMARY KEY | pk_mag_inv | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_invetario_data | `CREATE INDEX ix_mag_invetario_data ON magazzino.inventari USING btree (data)` |
| ix_mag_invetario_stato_inventario | `CREATE INDEX ix_mag_invetario_stato_inventario ON magazzino.inventari USING btree (stato_mag_inventario)` |
| pk_mag_inv | `CREATE UNIQUE INDEX pk_mag_inv ON magazzino.inventari USING btree (id)` |
| uq_mag_invetario_sorgente_fk | `CREATE UNIQUE INDEX uq_mag_invetario_sorgente_fk ON magazzino.inventari USING btree (sorgente_tipo_id, sorgente_uid) WHERE ((sorgente_tipo_id IS NOT NULL) AND (sorgente_uid IS NOT NULL))` |

---
{% include-markdown "signature-core.md" %}
