{% include-markdown "it/dbzero/anagrafiche/manual/istanze_dati_precontrattuali.md" %}
# 📚 Tabella `istanze_dati_precontrattuali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| istanza_utility_id | integer | NO |  |
| utility_id | integer | NO |  |
| stato | character varying | YES | 'RICEVUTO'::character varying |
| tipo_utenza_id | integer | YES |  |
| classe_utenza_id | integer | YES |  |
| param_1_num | numeric | YES |  |
| param_2_txt | character varying | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_idp_stato |  |
| FOREIGN KEY | fk_idp_classi_utenze | classe_utenza_id |
| FOREIGN KEY | fk_idp_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_idp_tipi_utenze | tipo_utenza_id |
| FOREIGN KEY | fk_idp_utilities | utility_id |
| PRIMARY KEY | pk_istanze_dati_precontrattuali | id |
| UNIQUE | uq_istanze_dati_precontrattuali_id_utility_id | istanza_utility_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_idp_classe_utenza_id | `CREATE INDEX ix_idp_classe_utenza_id ON anagrafiche.istanze_dati_precontrattuali USING btree (classe_utenza_id)` |
| ix_idp_istanza_utility_id | `CREATE INDEX ix_idp_istanza_utility_id ON anagrafiche.istanze_dati_precontrattuali USING btree (istanza_utility_id)` |
| ix_idp_tipo_utenza_id | `CREATE INDEX ix_idp_tipo_utenza_id ON anagrafiche.istanze_dati_precontrattuali USING btree (tipo_utenza_id)` |
| ix_idp_utility_id | `CREATE INDEX ix_idp_utility_id ON anagrafiche.istanze_dati_precontrattuali USING btree (utility_id)` |
| pk_istanze_dati_precontrattuali | `CREATE UNIQUE INDEX pk_istanze_dati_precontrattuali ON anagrafiche.istanze_dati_precontrattuali USING btree (id)` |
| uq_istanze_dati_precontrattuali_id_utility_id | `CREATE UNIQUE INDEX uq_istanze_dati_precontrattuali_id_utility_id ON anagrafiche.istanze_dati_precontrattuali USING btree (istanza_utility_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_istanze_dati_precontrattuali_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_dati_precontrattuali_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_istanze_dati_precontrattuali_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
