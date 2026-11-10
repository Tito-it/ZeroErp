{% include-markdown "it/dbzero/dbops/manual/lock_columns_conditional.md" %}
# 📚 Tabella `lock_columns_conditional`

> 📝 **Descrizione**
>
> Il registro dei lock condizionali: una colonna di una tabella che non si modifica quando condition_expr, valutata sulla riga, e' vera. condition_expr riceve l'id della riga come $1 (il cast al tipo della chiave lo scrive l'espressione, per esempio $1::uuid). Complementare a dbops.automation_lock_columns, i lock senza condizione. Lo legge dbops.fn_non_editable_fields, che da' al form i campi non modificabili di una riga; il rifiuto della modifica lo fa il guard della tabella, con lo stesso predicato. Si scrive solo da migrazione.

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
