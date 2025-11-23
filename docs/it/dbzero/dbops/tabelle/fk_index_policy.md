{% include-markdown "it/dbzero/dbops/manual/fk_index_policy.md" %}
# 📚 Tabella `fk_index_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_name | text | NO |  |
| constraint_name | text | NO |  |
| consentito | boolean | NO | true |
| dll_command | text | YES |  |
| generated_by_script | boolean | YES | false |
| user_insert | character varying | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | character varying | YES |  |
| data_update | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | fk_index_policy_pkey | schema_name, table_name, constraint_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| fk_index_policy_pkey | `CREATE UNIQUE INDEX fk_index_policy_pkey ON dbops.fk_index_policy USING btree (schema_name, table_name, constraint_name)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fk_index_policy_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
