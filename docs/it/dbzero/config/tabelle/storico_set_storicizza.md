{% include-markdown "it/dbzero/config/manual/storico_set_storicizza.md" %}
# 📚 Tabella `storico_set_storicizza`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| table_name | text | NO |  |
| insert_manuale | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | storico_set_storicizza_pkey | table_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| storico_set_storicizza_pkey | `CREATE UNIQUE INDEX storico_set_storicizza_pkey ON config.storico_set_storicizza USING btree (table_name)` |

---
{% include-markdown "signature-core.md" %}
