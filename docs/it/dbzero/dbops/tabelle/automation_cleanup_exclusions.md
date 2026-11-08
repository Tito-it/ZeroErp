{% include-markdown "it/dbzero/dbops/manual/automation_cleanup_exclusions.md" %}
# 📚 Tabella `automation_cleanup_exclusions`

> 📝 **Descrizione**
>
> Esclusioni tabelle per il framework di cleanup basato su cleanup_at.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_name | text | NO |  |
| enabled | boolean | NO | true |
| reason | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automation_cleanup_exclusions | schema_name, table_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_automation_cleanup_exclusions_enabled | `CREATE INDEX ix_automation_cleanup_exclusions_enabled ON dbops.automation_cleanup_exclusions USING btree (enabled)` |
| pk_automation_cleanup_exclusions | `CREATE UNIQUE INDEX pk_automation_cleanup_exclusions ON dbops.automation_cleanup_exclusions USING btree (schema_name, table_name)` |

---
{% include-markdown "signature-core.md" %}
