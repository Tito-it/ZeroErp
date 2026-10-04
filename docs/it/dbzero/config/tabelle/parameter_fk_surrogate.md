{% include-markdown "it/dbzero/config/manual/parameter_fk_surrogate.md" %}
# 📚 Tabella `parameter_fk_surrogate`

> 📝 **Descrizione**
>
> Registry pattern -&gt; tabella/colonna target per il framework FK-surrogata sui parametri. Letta dai dispatcher config.trgfn_parameters_fk_surrogate_dispatch e config.trgfn_parameter_overrides_fk_surrogate_dispatch.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| code_pattern | character varying(200) | NO |  |
| match_mode | character varying(10) | NO | 'EXACT'::character varying |
| target_schema | character varying(63) | NO |  |
| target_table | character varying(63) | NO |  |
| target_column | character varying(63) | NO | 'codice_interno'::character varying |
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
