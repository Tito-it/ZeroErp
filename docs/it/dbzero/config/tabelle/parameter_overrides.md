{% include-markdown "it/dbzero/config/manual/parameter_overrides.md" %}
# 📚 Tabella `parameter_overrides`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| parameter_id | bigint | NO |  |
| overridden_value | text | NO |  |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp without time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| session_key | text | YES |  |
| function_name | text | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| django_user_id | integer | YES |  |
| django_group_id | integer | YES |  |
| attivo | boolean | YES | true |
| emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_overrides_django_group | django_group_id |
| FOREIGN KEY | fk_overrides_django_user | django_user_id |
| FOREIGN KEY | fk_overrides_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_overrides_parameter | parameter_id |
| PRIMARY KEY | parameter_overrides_pkey | id |
| UNIQUE | uq_overrides_full_scope_v3 | parameter_id, emittente_fiscale_id, django_user_id, django_group_id, session_key, function_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_overrides_param_group | `CREATE INDEX ix_overrides_param_group ON config.parameter_overrides USING btree (parameter_id, django_group_id)` |
| ix_overrides_param_user | `CREATE INDEX ix_overrides_param_user ON config.parameter_overrides USING btree (parameter_id, django_user_id)` |
| ix_parameter_overrides_emittente | `CREATE INDEX ix_parameter_overrides_emittente ON config.parameter_overrides USING btree (parameter_id, emittente_fiscale_id)` |
| parameter_overrides_pkey | `CREATE UNIQUE INDEX parameter_overrides_pkey ON config.parameter_overrides USING btree (id)` |
| uq_overrides_full_scope_v3 | `CREATE UNIQUE INDEX uq_overrides_full_scope_v3 ON config.parameter_overrides USING btree (parameter_id, emittente_fiscale_id, django_user_id, django_group_id, session_key, function_name)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_parameter_overrides_a10_emittenti_fiscali_require_at_d95c44 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_parameter_overrides_a10_emittenti_fiscali_require_at_d95c44 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_parameter_overrides_a10_fk_surrogate_dispatch_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_parameter_overrides_fk_surrogate_dispatch()` |
| trg_parameter_overrides_a10_fk_surrogate_dispatch_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_parameter_overrides_fk_surrogate_dispatch()` |
| trg_parameter_overrides_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_parameter_overrides_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_parameter_overrides_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameter_overrides_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameter_overrides_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('parameter_override_id')` |
| trg_parameter_overrides_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('parameter_override_id')` |

---
{% include-markdown "signature-core.md" %}
