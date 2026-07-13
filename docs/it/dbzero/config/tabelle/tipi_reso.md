# 📚 Tabella `tipi_reso`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| riapre_residuo | boolean | NO |  |
| attivo | boolean | NO | true |
| ordine | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_reso | id |
| UNIQUE | uq_tipi_reso_codice | codice |
| UNIQUE | uq_tipi_reso_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_reso_attivo | `CREATE INDEX ix_tipi_reso_attivo ON config.tipi_reso USING btree (attivo)` |
| ix_tipi_reso_ordine | `CREATE INDEX ix_tipi_reso_ordine ON config.tipi_reso USING btree (ordine)` |
| pk_tipi_reso | `CREATE UNIQUE INDEX pk_tipi_reso ON config.tipi_reso USING btree (id)` |
| uq_tipi_reso_codice | `CREATE UNIQUE INDEX uq_tipi_reso_codice ON config.tipi_reso USING btree (codice)` |
| uq_tipi_reso_codice_interno | `CREATE UNIQUE INDEX uq_tipi_reso_codice_interno ON config.tipi_reso USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
