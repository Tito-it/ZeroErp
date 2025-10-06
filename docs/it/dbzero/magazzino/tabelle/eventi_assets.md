# 📚 Tabella `eventi_assets`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| asset_id | bigint | NO |  |
| data_evento | timestamp with time zone | NO | now() |
| magazzino_id_from | bigint | YES |  |
| magazzino_id_to | bigint | YES |  |
| doc_schema | character varying | YES |  |
| doc_table | character varying | YES |  |
| doc_id | bigint | YES |  |
| doc_riga_id | bigint | YES |  |
| attivo | boolean | NO | true |
| extra_info | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | character varying | YES |  |
| user_update | character varying | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |
| storicizza | boolean | NO | false |
| tipo_evento_id | bigint | NO |  |
| stato_da_id | bigint | YES |  |
| stato_a_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_eventi_assets_da_a_distinti |  |
| FOREIGN KEY | fk_mag_eventi_assets_asset | asset_id |
| FOREIGN KEY | fk_mag_eventi_assets_magazzino_from | magazzino_id_from |
| FOREIGN KEY | fk_mag_eventi_assets_magazzino_to | magazzino_id_to |
| FOREIGN KEY | fk_mag_eventi_assets_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_mag_eventi_assets_tipo_evento | tipo_evento_id |
| PRIMARY KEY | pk_mag_eventi_assets | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_eventi_assets_asset | `CREATE INDEX ix_mag_eventi_assets_asset ON magazzino.eventi_assets USING btree (asset_id)` |
| ix_mag_eventi_assets_data | `CREATE INDEX ix_mag_eventi_assets_data ON magazzino.eventi_assets USING btree (data_evento)` |
| ix_mag_eventi_assets_stato_a_id | `CREATE INDEX ix_mag_eventi_assets_stato_a_id ON magazzino.eventi_assets USING btree (stato_a_id)` |
| ix_mag_eventi_assets_stato_da_id | `CREATE INDEX ix_mag_eventi_assets_stato_da_id ON magazzino.eventi_assets USING btree (stato_da_id)` |
| ix_mag_eventi_assets_tipo_evento_id | `CREATE INDEX ix_mag_eventi_assets_tipo_evento_id ON magazzino.eventi_assets USING btree (tipo_evento_id)` |
| pk_mag_eventi_assets | `CREATE UNIQUE INDEX pk_mag_eventi_assets ON magazzino.eventi_assets USING btree (id)` |
| uq_mag_eventi_assets_sorgente_fk | `CREATE UNIQUE INDEX uq_mag_eventi_assets_sorgente_fk ON magazzino.eventi_assets USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_tipo_id IS NOT NULL)` |

---
{% include-markdown "signature-core.md" %}
