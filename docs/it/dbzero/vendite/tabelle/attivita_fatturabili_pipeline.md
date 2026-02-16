{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili_pipeline.md" %}
# 📚 Tabella `attivita_fatturabili_pipeline`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_step | text | NO |  |
| descrizione | text | YES |  |
| ordine | smallint | NO | 10 |
| processi | jsonb | NO | '[]'::jsonb |
| rollback | jsonb | NO | '[]'::jsonb |
| utility_id | integer | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_attivita_fatturabili_pipeline_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_attivita_fatturabili_pipeline_utility | utility_id |
| PRIMARY KEY | pk_attivita_fatturabili_pipeline | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_attivita_fatturabili_pipeline | `CREATE UNIQUE INDEX pk_attivita_fatturabili_pipeline ON vendite.attivita_fatturabili_pipeline USING btree (id)` |
| uq_attivita_pipeline_step_fallback | `CREATE UNIQUE INDEX uq_attivita_pipeline_step_fallback ON vendite.attivita_fatturabili_pipeline USING btree (codice_step) WHERE ((utility_id IS NULL) AND (sorgente_tipo_id IS NULL))` |
| uq_attivita_pipeline_step_sorgente | `CREATE UNIQUE INDEX uq_attivita_pipeline_step_sorgente ON vendite.attivita_fatturabili_pipeline USING btree (codice_step, sorgente_tipo_id) WHERE ((utility_id IS NULL) AND (sorgente_tipo_id IS NOT NULL))` |
| uq_attivita_pipeline_step_utility | `CREATE UNIQUE INDEX uq_attivita_pipeline_step_utility ON vendite.attivita_fatturabili_pipeline USING btree (codice_step, utility_id) WHERE ((utility_id IS NOT NULL) AND (sorgente_tipo_id IS NULL))` |
| uq_attivita_pipeline_step_utility_sorgente | `CREATE UNIQUE INDEX uq_attivita_pipeline_step_utility_sorgente ON vendite.attivita_fatturabili_pipeline USING btree (codice_step, utility_id, sorgente_tipo_id) WHERE ((utility_id IS NOT NULL) AND (sorgente_tipo_id IS NOT NULL))` |

---
{% include-markdown "signature-core.md" %}
