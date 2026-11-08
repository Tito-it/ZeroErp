{% include-markdown "it/dbzero/dbops/manual/pipeline_task_registry_impl.md" %}
# 📚 Tabella `pipeline_task_registry_impl`

> 📝 **Descrizione**
>
> Implementazioni consentite per task pipeline.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| task_registry_id | bigint | NO |  |
| implementation_key | text | NO |  |
| handler_code | text | NO |  |
| is_default | boolean | NO | false |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_pipeline_task_registry_impl_task | task_registry_id |
| PRIMARY KEY | pk_pipeline_task_registry_impl | id |
| UNIQUE | uq_pipeline_task_registry_impl_key | task_registry_id, implementation_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pipeline_task_registry_impl | `CREATE UNIQUE INDEX pk_pipeline_task_registry_impl ON dbops.pipeline_task_registry_impl USING btree (id)` |
| uq_pipeline_task_registry_impl_default | `CREATE UNIQUE INDEX uq_pipeline_task_registry_impl_default ON dbops.pipeline_task_registry_impl USING btree (task_registry_id) WHERE (is_default IS TRUE)` |
| uq_pipeline_task_registry_impl_key | `CREATE UNIQUE INDEX uq_pipeline_task_registry_impl_key ON dbops.pipeline_task_registry_impl USING btree (task_registry_id, implementation_key)` |

---
{% include-markdown "signature-core.md" %}
