# 📚 Tabella `automation_scope`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_like | text | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automation_scope | schema_name, table_like |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automation_scope | `CREATE UNIQUE INDEX pk_automation_scope ON dbops.automation_scope USING btree (schema_name, table_like)` |

---
{% include-markdown "signature-core.md" %}
