{% include-markdown "it/dbzero/config/manual/parameter_overrides.md" %}
# 📚 Tabella `parameter_overrides`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| parameter_id | bigint | NO |  |
| overridden_value | text | NO |  |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO | 'CURRENT_USER'::character varying |
| data_update | timestamp without time zone | NO | now() |
| user_update | character varying | NO | 'CURRENT_USER'::character varying |
| tenant_id | integer | YES |  |
| user_id | integer | YES |  |
| session_key | text | YES |  |
| function_name | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_overrides_parameter | parameter_id |
| PRIMARY KEY | parameter_overrides_pkey | id |
| UNIQUE | uq_overrides_full_scope | user_id, session_key, function_name, tenant_id, parameter_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| parameter_overrides_pkey | `CREATE UNIQUE INDEX parameter_overrides_pkey ON config.parameter_overrides USING btree (id)` |
| uq_overrides_full_scope | `CREATE UNIQUE INDEX uq_overrides_full_scope ON config.parameter_overrides USING btree (parameter_id, tenant_id, user_id, session_key, function_name)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_overrides_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
