{% include-markdown "it/dbzero/dbops/manual/fk_index_policy.md" %}
# 📚 Tabella `fk_index_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_name | text | NO |  |
| constraint_name | text | NO |  |
| consentito | boolean | NO | true |
| dll_command | text | NO |  |
| generated_by_script | boolean | YES | false |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fk_index_policy_dll_command_forma |  |
| PRIMARY KEY | fk_index_policy_pkey | schema_name, table_name, constraint_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| fk_index_policy_pkey | `CREATE UNIQUE INDEX fk_index_policy_pkey ON dbops.fk_index_policy USING btree (schema_name, table_name, constraint_name)` |

---
{% include-markdown "signature-core.md" %}
