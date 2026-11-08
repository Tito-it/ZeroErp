{% include-markdown "it/dbzero/dbops/manual/lock_columns_conditional.md" %}
# 📚 Tabella `lock_columns_conditional`

> 📝 **Descrizione**
>
> Registro lock condizionali: colonne immutabili SE condition_expr valutata sul record indicato da $1 (id come text) ritorna TRUE. Complementare a dbops.automation_lock_columns (lock statici). Scrivibile solo via migration. rev 2026-05-22.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| column_name | text | NO |  |
| condition_expr | text | NO |  |
| descrizione | text | YES |  |
| enabled | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | lock_columns_conditional_pkey | id |
| UNIQUE | uq_lock_columns_conditional | schema_name, table_name, column_name, condition_expr |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| lock_columns_conditional_pkey | `CREATE UNIQUE INDEX lock_columns_conditional_pkey ON dbops.lock_columns_conditional USING btree (id)` |
| uq_lock_columns_conditional | `CREATE UNIQUE INDEX uq_lock_columns_conditional ON dbops.lock_columns_conditional USING btree (schema_name, table_name, column_name, condition_expr)` |

---
{% include-markdown "signature-core.md" %}
