{% include-markdown "it/dbzero/catalogo/manual/uom_tipi.md" %}
# 📚 Tabella `uom_tipi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_uom_tipi | id |
| UNIQUE | uq_uom_tipi_codice | codice |
| UNIQUE | uq_uom_tipi_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_uom_tipi_codice_interno_upper | `CREATE INDEX ix_uom_tipi_codice_interno_upper ON catalogo.uom_tipi USING btree (upper((codice_interno)::text))` |
| ix_uom_tipi_codice_upper | `CREATE INDEX ix_uom_tipi_codice_upper ON catalogo.uom_tipi USING btree (upper((codice)::text))` |
| pk_uom_tipi | `CREATE UNIQUE INDEX pk_uom_tipi ON catalogo.uom_tipi USING btree (id)` |
| uq_uom_tipi_codice | `CREATE UNIQUE INDEX uq_uom_tipi_codice ON catalogo.uom_tipi USING btree (codice)` |
| uq_uom_tipi_codice_interno | `CREATE UNIQUE INDEX uq_uom_tipi_codice_interno ON catalogo.uom_tipi USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
