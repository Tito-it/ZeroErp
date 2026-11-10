{% include-markdown "it/dbzero/vendite/manual/fatturazione_pipeline.md" %}
# 📚 Tabella `fatturazione_pipeline`

> 📝 **Descrizione**
>
> Configurazione pipeline fatturazione per step, processi e rollback.

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
| tipo_lotto | text | NO | 'MASSIVO'::text |
| utility_id | integer | YES |  |
| tipo_doc_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_pipeline_tipo_lotto |  |
| FOREIGN KEY | fk_fatturazione_pipeline_stato_doc_fiscale | stato_doc_fiscale_id |
| FOREIGN KEY | fk_fatturazione_pipeline_tipo_doc_fiscale | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_fatturazione_pipeline_utility | utility_id |
| PRIMARY KEY | pk_fatturazione_pipeline | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_pipeline | `CREATE UNIQUE INDEX pk_fatturazione_pipeline ON vendite.fatturazione_pipeline USING btree (id)` |
| uq_fatt_pipeline_tipo_stato_fallback | `CREATE UNIQUE INDEX uq_fatt_pipeline_tipo_stato_fallback ON vendite.fatturazione_pipeline USING btree (tipo_lotto, stato_doc_fiscale_id) WHERE ((utility_id IS NULL) AND (tipo_doc_fiscale_id IS NULL))` |
| uq_fatt_pipeline_tipo_stato_tipodoc | `CREATE UNIQUE INDEX uq_fatt_pipeline_tipo_stato_tipodoc ON vendite.fatturazione_pipeline USING btree (tipo_lotto, stato_doc_fiscale_id, tipo_doc_fiscale_id) WHERE ((utility_id IS NULL) AND (tipo_doc_fiscale_id IS NOT NULL))` |
| uq_fatt_pipeline_tipo_stato_utility | `CREATE UNIQUE INDEX uq_fatt_pipeline_tipo_stato_utility ON vendite.fatturazione_pipeline USING btree (tipo_lotto, stato_doc_fiscale_id, utility_id) WHERE ((utility_id IS NOT NULL) AND (tipo_doc_fiscale_id IS NULL))` |
| uq_fatt_pipeline_tipo_stato_utility_tipodoc | `CREATE UNIQUE INDEX uq_fatt_pipeline_tipo_stato_utility_tipodoc ON vendite.fatturazione_pipeline USING btree (tipo_lotto, stato_doc_fiscale_id, utility_id, tipo_doc_fiscale_id) WHERE ((utility_id IS NOT NULL) AND (tipo_doc_fiscale_id IS NOT NULL))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_pipeline_a10_fatturazione_lotti_task_ru_5f19a9 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti_task_runs', 'pipeline_id', 'id', 'attivo')` |
| trg_fatturazione_pipeline_a10_fatturazione_pipeline_task_16b97a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_pipeline_task_policy', 'pipeline_id', 'id', 'attivo')` |
| trg_fatturazione_pipeline_a10_stati_doc_fiscale_require_cbe8f7 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_pipeline_a10_stati_doc_fiscale_require_cbe8f7 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_pipeline_a10_tipi_doc_fiscale_require_a_50168f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatturazione_pipeline_a10_tipi_doc_fiscale_require_a_50168f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatturazione_pipeline_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_pipeline_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
