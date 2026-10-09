{% include-markdown "it/dbzero/config/manual/user_override_oggetti.md" %}
# 📚 Tabella `user_override_oggetti`

> 📝 **Descrizione**
>
> Override individuale su singolo model Django.
>  Sovrascrive sia il profilo reparto che l'override area.
>  Esempio: utente ha TUTTO su anagrafiche ma LETTURA su anagrafiche.clienti.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| app_label | character varying(100) | NO |  |
| model_name | character varying(100) | NO |  |
| livello | config.livello_accesso | NO |  |
| motivo | text | YES |  |
| valido_dal | date | YES | script.fn_data_operativa() |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| validita | daterange | NO |  |
| riservato | boolean | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_user_override_oggetti_validita |  |
| FOREIGN KEY | fk_config_user_override_oggetti_auth_user | auth_user_id |
| FOREIGN KEY | fk_user_override_oggetti_catalogo | app_label, model_name, riservato |
| PRIMARY KEY | pk_user_override_oggetti | id |
| UNIQUE | uq_user_override_oggetti_user_app_model | auth_user_id, app_label, model_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_user_override_oggetti | `CREATE UNIQUE INDEX pk_user_override_oggetti ON config.user_override_oggetti USING btree (id)` |
| uq_user_override_oggetti_user_app_model | `CREATE UNIQUE INDEX uq_user_override_oggetti_user_app_model ON config.user_override_oggetti USING btree (auth_user_id, app_label, model_name)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_user_override_oggetti_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_user_override_oggetti_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_user_override_oggetti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_override_oggetti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_override_oggetti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_override_oggetti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_override_oggetti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('user_override_oggetti_id')` |
| trg_user_override_oggetti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('user_override_oggetti_id')` |

---
{% include-markdown "signature-core.md" %}
