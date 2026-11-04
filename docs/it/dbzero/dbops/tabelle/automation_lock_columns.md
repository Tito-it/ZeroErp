{% include-markdown "it/dbzero/dbops/manual/automation_lock_columns.md" %}
# 📚 Tabella `automation_lock_columns`

> 📝 **Descrizione**
>
> Configura colonne extra da bloccare (codice_interno e' implicito).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| target_schema | text | NO |  |
| target_table | text | NO |  |
| column_name | text | NO |  |
| error_code | text | NO |  |
| exec_mode | text | NO | 'AUTO'::text |
| enabled | boolean | NO | true |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automation_lock_columns | target_schema, target_table, column_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automation_lock_columns | `CREATE UNIQUE INDEX pk_automation_lock_columns ON dbops.automation_lock_columns USING btree (target_schema, target_table, column_name)` |

---
{% include-markdown "signature-core.md" %}
