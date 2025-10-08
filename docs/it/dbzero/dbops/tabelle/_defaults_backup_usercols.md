# 📚 Tabella `_defaults_backup_usercols`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| column_name | text | NO |  |
| old_default_expr | text | NO |  |
| captured_at | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | _defaults_backup_usercols_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| _defaults_backup_usercols_pkey | `CREATE UNIQUE INDEX _defaults_backup_usercols_pkey ON dbops._defaults_backup_usercols USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
