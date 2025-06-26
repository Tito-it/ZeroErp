# 📚 Tabella `billing_account`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.billing_account_id_seq'::regclass) |
| istanza_id | integer | NO |  |
| soggetto_ruolo_id | integer | NO |  |
| utility_id | integer | NO |  |
| parent_account_id | integer | YES |  |
| account_code | character varying | NO |  |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_billing_account_anagrafiche | parent_account_id |
| FOREIGN KEY | fk_istanze_utilities_anagrafiche | istanza_id, istanza_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_billing_account | id |
| UNIQUE | uq_billing_account_code | account_code |
| UNIQUE | uq_billing_instance_utility | istanza_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_billing_account_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_billing_account_soggetto_ruolo_id ON anagrafiche.billing_account USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_billing_account_utility_id | `CREATE INDEX ix_anagrafiche_billing_account_utility_id ON anagrafiche.billing_account USING btree (utility_id)` |
| ix_billing_account_istanza | `CREATE INDEX ix_billing_account_istanza ON anagrafiche.billing_account USING btree (istanza_id)` |
| ix_billing_account_parent | `CREATE INDEX ix_billing_account_parent ON anagrafiche.billing_account USING btree (parent_account_id)` |
| pk_billing_account | `CREATE UNIQUE INDEX pk_billing_account ON anagrafiche.billing_account USING btree (id)` |
| uq_billing_account_code | `CREATE UNIQUE INDEX uq_billing_account_code ON anagrafiche.billing_account USING btree (account_code)` |
| uq_billing_instance_utility | `CREATE UNIQUE INDEX uq_billing_instance_utility ON anagrafiche.billing_account USING btree (istanza_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_billing_account_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |