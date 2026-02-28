{% include-markdown "it/dbzero/config/manual/aree_funzionali.md" %}
# 📚 Tabella `aree_funzionali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO |  |
| schema_db | character varying | NO |  |
| attivo | boolean | NO | true |
| ordinamento | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_aree_funzionali | id |
| UNIQUE | uq_aree_funzionali_codice | codice |
| UNIQUE | uq_aree_funzionali_codice_interno | codice_interno |
| UNIQUE | uq_aree_funzionali_schema_db | schema_db |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_aree_funzionali | `CREATE UNIQUE INDEX pk_aree_funzionali ON config.aree_funzionali USING btree (id)` |
| uq_aree_funzionali_codice | `CREATE UNIQUE INDEX uq_aree_funzionali_codice ON config.aree_funzionali USING btree (codice)` |
| uq_aree_funzionali_codice_interno | `CREATE UNIQUE INDEX uq_aree_funzionali_codice_interno ON config.aree_funzionali USING btree (codice_interno)` |
| uq_aree_funzionali_schema_db | `CREATE UNIQUE INDEX uq_aree_funzionali_schema_db ON config.aree_funzionali USING btree (schema_db)` |

---
{% include-markdown "signature-core.md" %}
