{% include-markdown "it/dbzero/anagrafiche/manual/istanze_dati_precontrattuali.md" %}
# 📚 Tabella `istanze_dati_precontrattuali`

> 📝 **Descrizione**
>
> Dati tecnici precontrattuali per istanze utilities: parametri di profilazione e condizioni preliminari (core + JSONB).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| classe_utenza_id | integer | YES |  |
| param_1_num | numeric(18,6) | YES |  |
| param_2_txt | character varying(80) | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_istanze_dati_precontrattuali_param_1_num_finito |  |
| FOREIGN KEY | fk_idp_billing_account_coppia | istanza_utility_id, utility_id |
| FOREIGN KEY | fk_idp_classi_utenze | classe_utenza_id |
| FOREIGN KEY | fk_idp_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_idp_utilities | utility_id |
| PRIMARY KEY | pk_istanze_dati_precontrattuali | id |
| UNIQUE | uq_istanze_dati_precontrattuali_id_utility_id | istanza_utility_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_istanze_dati_precontrattuali_classe_utenza_id | `CREATE INDEX ix_anagrafiche_istanze_dati_precontrattuali_classe_utenza_id ON anagrafiche.istanze_dati_precontrattuali USING btree (classe_utenza_id)` |
| ix_anagrafiche_istanze_dati_precontrattuali_utility_id | `CREATE INDEX ix_anagrafiche_istanze_dati_precontrattuali_utility_id ON anagrafiche.istanze_dati_precontrattuali USING btree (utility_id)` |
| pk_istanze_dati_precontrattuali | `CREATE UNIQUE INDEX pk_istanze_dati_precontrattuali ON anagrafiche.istanze_dati_precontrattuali USING btree (id)` |
| uq_istanze_dati_precontrattuali_id_utility_id | `CREATE UNIQUE INDEX uq_istanze_dati_precontrattuali_id_utility_id ON anagrafiche.istanze_dati_precontrattuali USING btree (istanza_utility_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_istanze_dati_precontrattuali_a10_protect_update_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update()` |
| trg_istanze_dati_precontrattuali_a10_protect_update_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_dati_precontrattuali_protect_update()` |
| trg_istanze_dati_precontrattuali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_istanze_dati_precontrattuali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_istanze_dati_precontrattuali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_dati_precontrattuali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_dati_precontrattuali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('istanze_dati_precontrattuali_id')` |
| trg_istanze_dati_precontrattuali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('istanze_dati_precontrattuali_id')` |

---
{% include-markdown "signature-core.md" %}
