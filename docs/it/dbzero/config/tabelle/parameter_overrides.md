{% include-markdown "it/dbzero/config/manual/parameter_overrides.md" %}
# 📚 Tabella `parameter_overrides`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| parameter_id | bigint | NO |  |
| overridden_value | text | NO |  |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp without time zone | NO | now() |
| user_update | character varying | NO | CURRENT_USER |
| tenant_id | integer | YES |  |
| session_key | text | YES |  |
| function_name | text | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| django_user_id | integer | YES |  |
| django_group_id | integer | YES |  |
| attivo | boolean | YES | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_overrides_has_scope |  |
| FOREIGN KEY | fk_overrides_django_group | django_group_id |
| FOREIGN KEY | fk_overrides_django_user | django_user_id |
| FOREIGN KEY | fk_overrides_parameter | parameter_id |
| PRIMARY KEY | parameter_overrides_pkey | id |
| UNIQUE | uq_overrides_full_scope_v2 | session_key, django_user_id, tenant_id, django_group_id, parameter_id, function_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_overrides_param_group | `CREATE INDEX ix_overrides_param_group ON config.parameter_overrides USING btree (parameter_id, django_group_id)` |
| ix_overrides_param_tenant | `CREATE INDEX ix_overrides_param_tenant ON config.parameter_overrides USING btree (parameter_id, tenant_id)` |
| ix_overrides_param_user | `CREATE INDEX ix_overrides_param_user ON config.parameter_overrides USING btree (parameter_id, django_user_id)` |
| parameter_overrides_pkey | `CREATE UNIQUE INDEX parameter_overrides_pkey ON config.parameter_overrides USING btree (id)` |
| uq_overrides_full_scope_v2 | `CREATE UNIQUE INDEX uq_overrides_full_scope_v2 ON config.parameter_overrides USING btree (parameter_id, tenant_id, django_user_id, django_group_id, session_key, function_name)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_parameter_overrides_ins_upd_tx_id_managed | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameter_overrides_ins_upd_tx_id_managed | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameter_overrides_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_parameter_overrides_z90_upd_dlt_storico_generic | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('parameter_override_id')` |
| trg_parameter_overrides_z90_upd_dlt_storico_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('parameter_override_id')` |

---
{% include-markdown "signature-core.md" %}
