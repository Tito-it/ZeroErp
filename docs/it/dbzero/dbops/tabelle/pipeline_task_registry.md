{% include-markdown "it/dbzero/dbops/manual/pipeline_task_registry.md" %}
# 📚 Tabella `pipeline_task_registry`

> 📝 **Descrizione**
>
> Catalogo task ammessi per dominio pipeline.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| dominio_id | bigint | NO |  |
| task_code | text | NO |  |
| descrizione | text | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_pipeline_task_registry_dominio | dominio_id |
| PRIMARY KEY | pk_pipeline_task_registry | id |
| UNIQUE | uq_pipeline_task_registry_dom_task | dominio_id, task_code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pipeline_task_registry | `CREATE UNIQUE INDEX pk_pipeline_task_registry ON dbops.pipeline_task_registry USING btree (id)` |
| uq_pipeline_task_registry_dom_task | `CREATE UNIQUE INDEX uq_pipeline_task_registry_dom_task ON dbops.pipeline_task_registry USING btree (dominio_id, task_code)` |

---
{% include-markdown "signature-core.md" %}
