{% include-markdown "it/dbzero/config/manual/tipi_allegato.md" %}
# 📚 Tabella `tipi_allegato`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_allegato | id |
| UNIQUE | uq_tipi_allegato_codice | codice |
| UNIQUE | uq_tipi_allegato_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_allegato | `CREATE UNIQUE INDEX pk_tipi_allegato ON config.tipi_allegato USING btree (id)` |
| uq_tipi_allegato_codice | `CREATE UNIQUE INDEX uq_tipi_allegato_codice ON config.tipi_allegato USING btree (codice)` |
| uq_tipi_allegato_codice_interno | `CREATE UNIQUE INDEX uq_tipi_allegato_codice_interno ON config.tipi_allegato USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
