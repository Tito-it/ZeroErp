{% include-markdown "it/dbzero/dbops/manual/automation_delete_block.md" %}
# 📚 Tabella `automation_delete_block`

> 📝 **Descrizione**
>
> Configurazione trigger delete-block per tabelle sensibili (ruoli).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| guc_key | text | NO |  |
| enabled | boolean | NO | true |
| trigger_name | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automation_delete_block | id |
| UNIQUE | uq_automation_delete_block_table | schema_name, table_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automation_delete_block | `CREATE UNIQUE INDEX pk_automation_delete_block ON dbops.automation_delete_block USING btree (id)` |
| uq_automation_delete_block_table | `CREATE UNIQUE INDEX uq_automation_delete_block_table ON dbops.automation_delete_block USING btree (schema_name, table_name)` |

---
{% include-markdown "signature-core.md" %}
