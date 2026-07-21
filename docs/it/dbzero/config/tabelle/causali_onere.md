# 📚 Tabella `causali_onere`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
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
| PRIMARY KEY | pk_causali_onere | id |
| UNIQUE | uq_causali_onere_codice | codice |
| UNIQUE | uq_causali_onere_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_causali_onere_attivo | `CREATE INDEX ix_causali_onere_attivo ON config.causali_onere USING btree (attivo)` |
| ix_causali_onere_ordine | `CREATE INDEX ix_causali_onere_ordine ON config.causali_onere USING btree (ordine)` |
| pk_causali_onere | `CREATE UNIQUE INDEX pk_causali_onere ON config.causali_onere USING btree (id)` |
| uq_causali_onere_codice | `CREATE UNIQUE INDEX uq_causali_onere_codice ON config.causali_onere USING btree (codice)` |
| uq_causali_onere_codice_interno | `CREATE UNIQUE INDEX uq_causali_onere_codice_interno ON config.causali_onere USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
