{% include-markdown "it/dbzero/config/manual/parameters.md" %}
# 📚 Tabella `parameters`

> 📝 **Descrizione**
>
> Catalogo dei parametri di sistema, con valore di default e descrizione

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| code | character varying(100) | NO |  |
| default_value | text | NO |  |
| description | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| ammette_override | boolean | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | parameters_pkey | id |
| UNIQUE | uq_parameters_code | code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| parameters_pkey | `CREATE UNIQUE INDEX parameters_pkey ON config.parameters USING btree (id)` |
| uq_parameters_code | `CREATE UNIQUE INDEX uq_parameters_code ON config.parameters USING btree (code)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_parameters_a10_fk_surrogate_dispatch_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_parameters_fk_surrogate_dispatch()` |
| trg_parameters_a10_fk_surrogate_dispatch_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_parameters_fk_surrogate_dispatch()` |
| trg_parameters_a10_guard_ammette_override_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_parameters_guard_ammette_override()` |
| trg_parameters_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_parameters_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_parameters_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameters_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameters_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('parameters_id')` |
| trg_parameters_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('parameters_id')` |

---
{% include-markdown "signature-core.md" %}
