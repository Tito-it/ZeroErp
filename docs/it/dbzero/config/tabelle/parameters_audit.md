{% include-markdown "it/dbzero/config/manual/parameters_audit.md" %}
# 📚 Tabella `parameters_audit`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| parameter_code | character varying | NO |  |
| action | character varying | NO |  |
| old_value | text | YES |  |
| new_value | text | NO |  |
| reason | text | YES |  |
| user_insert | character varying | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_parameters_audit_parameter_code | parameter_code |
| PRIMARY KEY | parameters_audit_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| parameters_audit_pkey | `CREATE UNIQUE INDEX parameters_audit_pkey ON config.parameters_audit USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_prevent_mod_parameters_audit | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_prevent_modification_generic()` |
| trg_prevent_mod_parameters_audit | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_prevent_modification_generic()` |