{% include-markdown "it/dbzero/anagrafiche/manual/billing_account.md" %}
# 📚 Tabella `billing_account`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| istanza_utility_id | integer | NO |  |
| soggetto_ruolo_id | integer | NO |  |
| utility_id | integer | NO |  |
| parent_account_id | integer | YES |  |
| codice | character varying | NO |  |
| valid_from | date | YES | CURRENT_DATE |
| valid_to | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_billing_account_anagrafiche | parent_account_id |
| FOREIGN KEY | fk_billing_account_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_billing_account | id |
| UNIQUE | uq_billing_account_codice | codice |
| UNIQUE | uq_billing_instance_utility | utility_id, istanza_utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_billing_account_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_billing_account_soggetto_ruolo_id ON anagrafiche.billing_account USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_billing_account_utility_id | `CREATE INDEX ix_anagrafiche_billing_account_utility_id ON anagrafiche.billing_account USING btree (utility_id)` |
| ix_billing_account_istanza | `CREATE INDEX ix_billing_account_istanza ON anagrafiche.billing_account USING btree (istanza_utility_id)` |
| ix_billing_account_parent | `CREATE INDEX ix_billing_account_parent ON anagrafiche.billing_account USING btree (parent_account_id)` |
| pk_billing_account | `CREATE UNIQUE INDEX pk_billing_account ON anagrafiche.billing_account USING btree (id)` |
| uq_billing_account_codice | `CREATE UNIQUE INDEX uq_billing_account_codice ON anagrafiche.billing_account USING btree (codice)` |
| uq_billing_instance_utility | `CREATE UNIQUE INDEX uq_billing_instance_utility ON anagrafiche.billing_account USING btree (istanza_utility_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_billing_account_a10_protect_account_code_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_protect_account_code()` |
| trg_billing_account_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_billing_account_guard_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()` |
| trg_billing_account_guard_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()` |
| trg_billing_account_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_billing_account_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
