# 📚 Tabella `assets`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| seriale | character varying | NO |  |
| ownership | character varying | NO | 'owned'::character varying |
| billing_account_id | bigint | YES |  |
| contratto_id | bigint | YES |  |
| magazzino_id | bigint | YES |  |
| ubicazione | character varying | YES |  |
| data_stato | timestamp with time zone | NO | now() |
| note | text | YES |  |
| attivo | boolean | NO | true |
| extra_info | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | character varying | YES |  |
| user_update | character varying | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |
| storicizza | boolean | NO | false |
| stato_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_assets_articolo | articolo_id |
| FOREIGN KEY | fk_mag_assets_billing_account | billing_account_id |
| FOREIGN KEY | fk_mag_assets_contratto | contratto_id |
| FOREIGN KEY | fk_mag_assets_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_assets_stato | stato_id |
| PRIMARY KEY | pk_mag_assets | id |
| UNIQUE | uq_mag_assets_seriale | seriale |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_assets_articolo | `CREATE INDEX ix_mag_assets_articolo ON magazzino.assets USING btree (articolo_id)` |
| ix_mag_assets_magazzino | `CREATE INDEX ix_mag_assets_magazzino ON magazzino.assets USING btree (magazzino_id)` |
| ix_mag_assets_stato_id | `CREATE INDEX ix_mag_assets_stato_id ON magazzino.assets USING btree (stato_id)` |
| pk_mag_assets | `CREATE UNIQUE INDEX pk_mag_assets ON magazzino.assets USING btree (id)` |
| uq_mag_assets_seriale | `CREATE UNIQUE INDEX uq_mag_assets_seriale ON magazzino.assets USING btree (seriale)` |

---
{% include-markdown "signature-core.md" %}
