{% include-markdown "it/dbzero/vendite/manual/fatturazione_pipeline.md" %}
# 📚 Tabella `fatturazione_pipeline`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| descrizione | text | YES |  |
| stato_doc_fiscale_id | bigint | NO |  |
| processi | jsonb | NO | '[]'::jsonb |
| rollback | jsonb | NO | '[]'::jsonb |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatturazione_pipeline_stato_doc_fiscale | stato_doc_fiscale_id |
| PRIMARY KEY | pk_fatturazione_pipeline | id |
| UNIQUE | uq_fatturazione_pipeline_stato_doc_fiscale_id | stato_doc_fiscale_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_pipeline | `CREATE UNIQUE INDEX pk_fatturazione_pipeline ON vendite.fatturazione_pipeline USING btree (id)` |
| uq_fatturazione_pipeline_stato_doc_fiscale_id | `CREATE UNIQUE INDEX uq_fatturazione_pipeline_stato_doc_fiscale_id ON vendite.fatturazione_pipeline USING btree (stato_doc_fiscale_id)` |

---
{% include-markdown "signature-core.md" %}
