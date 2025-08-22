{% include-markdown "it/dbzero/dbops/manual/automation_fk_exclusions.md" %}
# 📚 Tabella `automation_fk_exclusions`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| parent_schema | text | NO |  |
| parent_table | text | NO |  |
| child_schema | text | NO |  |
| child_table | text | NO |  |
| reason | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automation_fk_exclusions | parent_schema, parent_table, child_schema, child_table |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automation_fk_exclusions | `CREATE UNIQUE INDEX pk_automation_fk_exclusions ON dbops.automation_fk_exclusions USING btree (parent_schema, parent_table, child_schema, child_table)` |

---
{% include-markdown "signature-core.md" %}
