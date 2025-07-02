# 📚 Tabella `istanze_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.istanze_utilities_id_seq'::regclass) |
| soggetto_ruolo_id | integer | NO |  |
| fittizia | boolean | NO | false |
| codice_istanza | character varying | NO |  |
| proprietario_inquilino | character | NO | 'I'::bpchar |
| destinazione_immobile | character | YES |  |
| num_concessione | character varying | YES |  |
| data_concessione | date | YES |  |
| sezione_catastale | character | YES |  |
| foglio_catastale | character | YES |  |
| particella | character | YES |  |
| subalterno | character | YES |  |
| anno_protocollo | integer | YES |  |
| superficie | integer | YES |  |
| immobile_rurale | boolean | NO | false |
| tipo_accatastamento | character | YES |  |
| categoria_catastale | character varying | YES |  |
| classe_catastale | character varying | YES |  |
| rendita_catastale | numeric | YES |  |
| consistenza | integer | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| account_code | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_istanza_utilities_imm_rurale |  |
| CHECK | chk_istanza_utilities_prop_inquilino |  |
| CHECK | chk_istanze_utilities_fittizia |  |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| PRIMARY KEY | pk_istanze_utilities | id |
| UNIQUE | uq_istanze_utilities_account_code | account_code |
| UNIQUE | uq_istanze_utilities_codice_istanza | codice_istanza |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_istanze_utilities_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_istanze_utilities_soggetto_ruolo_id ON anagrafiche.istanze_utilities USING btree (soggetto_ruolo_id)` |
| ix_istanze_utilities_soggetto_ruolo_id | `CREATE INDEX ix_istanze_utilities_soggetto_ruolo_id ON anagrafiche.istanze_utilities USING btree (soggetto_ruolo_id)` |
| pk_istanze_utilities | `CREATE UNIQUE INDEX pk_istanze_utilities ON anagrafiche.istanze_utilities USING btree (id)` |
| uq_istanze_utilities_account_code | `CREATE UNIQUE INDEX uq_istanze_utilities_account_code ON anagrafiche.istanze_utilities USING btree (account_code)` |
| uq_istanze_utilities_codice_istanza | `CREATE UNIQUE INDEX uq_istanze_utilities_codice_istanza ON anagrafiche.istanze_utilities USING btree (codice_istanza)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_istanze_utilities_ins_set_istanza_codice | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_ins_set_istanza_codice()` |
| trg_upd_istanze_utilities_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |