# 📚 Tabella `causali_trasporto`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_causali_trasporto | id |
| UNIQUE | causali_trasporto_codice_key | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| causali_trasporto_codice_key | `CREATE UNIQUE INDEX causali_trasporto_codice_key ON config.causali_trasporto USING btree (codice)` |
| ix_causali_trasporto_attivo | `CREATE INDEX ix_causali_trasporto_attivo ON config.causali_trasporto USING btree (attivo)` |
| pk_causali_trasporto | `CREATE UNIQUE INDEX pk_causali_trasporto ON config.causali_trasporto USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
