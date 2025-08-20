# 📚 Tabella `automation_overrides_cols`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_name | text | NO |  |
| col_role | text | NO |  |
| col_name | text | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automation_overrides_cols | schema_name, table_name, col_role |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automation_overrides_cols | `CREATE UNIQUE INDEX pk_automation_overrides_cols ON dbops.automation_overrides_cols USING btree (schema_name, table_name, col_role)` |

---
{% include-markdown "signature-core.md" %}
