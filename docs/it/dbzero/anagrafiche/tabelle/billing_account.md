{% include-markdown "it/dbzero/anagrafiche/manual/billing_account.md" %}
# 📚 Tabella `billing_account`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| utility_id | integer | NO |  |
| parent_account_id | bigint | YES |  |
| codice | character varying | NO |  |
| valido_dal | date | YES | CURRENT_DATE |
| valido_al | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| fatturazione_ordini | character varying | NO | 'CONFERMATO'::character varying |
| valuta_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_billing_account_fatturazione_ordini |  |
| CHECK | chk_billing_account_validita |  |
| FOREIGN KEY | fk_billing_account_anagrafiche | parent_account_id |
| FOREIGN KEY | fk_billing_account_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id |
| FOREIGN KEY | fk_utilities_config | utility_id |
| PRIMARY KEY | pk_billing_account | id |
| UNIQUE | uq_billing_account_codice | codice |
| UNIQUE | uq_billing_account_id_istanza_utility | id, istanza_utility_id |
| UNIQUE | uq_billing_instance_utility | istanza_utility_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_billing_account_istanza_utility_id | `CREATE INDEX ix_anagrafiche_billing_account_istanza_utility_id ON anagrafiche.billing_account USING btree (istanza_utility_id)` |
| ix_anagrafiche_billing_account_parent_account_id | `CREATE INDEX ix_anagrafiche_billing_account_parent_account_id ON anagrafiche.billing_account USING btree (parent_account_id)` |
| ix_anagrafiche_billing_account_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_billing_account_soggetto_ruolo_id ON anagrafiche.billing_account USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_billing_account_utility_id | `CREATE INDEX ix_anagrafiche_billing_account_utility_id ON anagrafiche.billing_account USING btree (utility_id)` |
| pk_billing_account | `CREATE UNIQUE INDEX pk_billing_account ON anagrafiche.billing_account USING btree (id)` |
| uq_billing_account_codice | `CREATE UNIQUE INDEX uq_billing_account_codice ON anagrafiche.billing_account USING btree (codice)` |
| uq_billing_account_id_istanza_utility | `CREATE UNIQUE INDEX uq_billing_account_id_istanza_utility ON anagrafiche.billing_account USING btree (id, istanza_utility_id)` |
| uq_billing_instance_utility | `CREATE UNIQUE INDEX uq_billing_instance_utility ON anagrafiche.billing_account USING btree (istanza_utility_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_billing_account_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_gen_codice()` |
| trg_billing_account_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_gen_codice()` |
| trg_billing_account_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')` |
| trg_billing_account_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_billing_account_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_billing_account_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_billing_account_guard_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()` |
| trg_billing_account_guard_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()` |
| trg_billing_account_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('billing_account_id')` |
| trg_billing_account_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('billing_account_id')` |

---
{% include-markdown "signature-core.md" %}
