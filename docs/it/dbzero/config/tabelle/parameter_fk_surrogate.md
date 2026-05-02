{% include-markdown "it/dbzero/config/manual/parameter_fk_surrogate.md" %}
# 📚 Tabella `parameter_fk_surrogate`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| code_pattern | character varying | NO |  |
| match_mode | character varying | NO | 'EXACT'::character varying |
| target_schema | character varying | NO |  |
| target_table | character varying | NO |  |
| target_column | character varying | NO | 'codice_interno'::character varying |
| enabled | boolean | NO | true |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_parameter_fk_surrogate_match_mode |  |
| PRIMARY KEY | pk_parameter_fk_surrogate | id |
| UNIQUE | uq_parameter_fk_surrogate_code_pattern | code_pattern |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_parameter_fk_surrogate | `CREATE UNIQUE INDEX pk_parameter_fk_surrogate ON config.parameter_fk_surrogate USING btree (id)` |
| uq_parameter_fk_surrogate_code_pattern | `CREATE UNIQUE INDEX uq_parameter_fk_surrogate_code_pattern ON config.parameter_fk_surrogate USING btree (code_pattern)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_parameter_fk_surrogate_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_parameter_fk_surrogate_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
