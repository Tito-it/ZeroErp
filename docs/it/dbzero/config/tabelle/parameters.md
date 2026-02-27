{% include-markdown "it/dbzero/config/manual/parameters.md" %}
# 📚 Tabella `parameters`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| code | character varying | NO |  |
| default_value | text | NO |  |
| description | text | YES |  |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp without time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |

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
| trg_parameters_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_parameters_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_parameters_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameters_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameters_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('parameters_id')` |
| trg_parameters_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('parameters_id')` |

---
{% include-markdown "signature-core.md" %}
