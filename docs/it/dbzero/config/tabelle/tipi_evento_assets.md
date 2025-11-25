# 📚 Tabella `tipi_evento_assets`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_evento_assets | id |
| UNIQUE | uq_tipi_evento_assets_codice | codice |
| UNIQUE | uq_tipi_evento_assets_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_evento_assets_attivo | `CREATE INDEX ix_tipi_evento_assets_attivo ON config.tipi_evento_assets USING btree (attivo)` |
| ix_tipi_evento_assets_codice_interno_upper | `CREATE INDEX ix_tipi_evento_assets_codice_interno_upper ON config.tipi_evento_assets USING btree (upper((codice_interno)::text))` |
| ix_tipi_evento_assets_codice_upper | `CREATE INDEX ix_tipi_evento_assets_codice_upper ON config.tipi_evento_assets USING btree (upper((codice)::text))` |
| ix_tipi_evento_assets_descrizione_upper | `CREATE INDEX ix_tipi_evento_assets_descrizione_upper ON config.tipi_evento_assets USING btree (upper((descrizione)::text))` |
| pk_tipi_evento_assets | `CREATE UNIQUE INDEX pk_tipi_evento_assets ON config.tipi_evento_assets USING btree (id)` |
| uq_tipi_evento_assets_codice | `CREATE UNIQUE INDEX uq_tipi_evento_assets_codice ON config.tipi_evento_assets USING btree (codice)` |
| uq_tipi_evento_assets_codice_interno | `CREATE UNIQUE INDEX uq_tipi_evento_assets_codice_interno ON config.tipi_evento_assets USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
