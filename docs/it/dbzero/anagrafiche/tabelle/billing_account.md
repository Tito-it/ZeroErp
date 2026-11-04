{% include-markdown "it/dbzero/anagrafiche/manual/billing_account.md" %}
# 📚 Tabella `billing_account`

> 📝 **Descrizione**
>
> Storico dei codici cliente definitivi per utility

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| utility_id | integer | NO |  |
| parent_account_id | bigint | YES |  |
| codice | character varying(30) | NO |  |
| valido_dal | date | YES | script.fn_data_operativa() |
| valido_al | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| fatturazione_ordini | character varying | NO | 'CONFERMATO'::character varying |
| valuta_id | integer | YES |  |
| categoria_cliente_id | smallint | NO |  |
| canale_origine | config.canale_origine | NO | 'ADMIN'::config.canale_origine |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_billing_account_fatturazione_ordini |  |
| CHECK | chk_billing_account_validita |  |
| FOREIGN KEY | fk_billing_account_anagrafiche | parent_account_id |
| FOREIGN KEY | fk_billing_account_categoria_cliente | categoria_cliente_id |
| FOREIGN KEY | fk_billing_account_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id |
| FOREIGN KEY | fk_utilities_config | utility_id |
| PRIMARY KEY | pk_billing_account | id |
| UNIQUE | uq_billing_account_codice | codice |
| UNIQUE | uq_billing_account_id_cliente | id, soggetto_ruolo_id, utility_id |
| UNIQUE | uq_billing_account_id_coppia | id, istanza_utility_id, utility_id |
| UNIQUE | uq_billing_account_id_istanza_utility | id, istanza_utility_id |
| UNIQUE | uq_billing_instance_utility | istanza_utility_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_billing_account_parent_account_id | `CREATE INDEX ix_anagrafiche_billing_account_parent_account_id ON anagrafiche.billing_account USING btree (parent_account_id)` |
| ix_anagrafiche_billing_account_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_billing_account_soggetto_ruolo_id ON anagrafiche.billing_account USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_billing_account_utility_id | `CREATE INDEX ix_anagrafiche_billing_account_utility_id ON anagrafiche.billing_account USING btree (utility_id)` |
| ix_billing_account_categoria_cliente | `CREATE INDEX ix_billing_account_categoria_cliente ON anagrafiche.billing_account USING btree (categoria_cliente_id)` |
| ix_billing_account_codice_trgm | `CREATE INDEX ix_billing_account_codice_trgm ON anagrafiche.billing_account USING gin (codice gin_trgm_ops)` |
| pk_billing_account | `CREATE UNIQUE INDEX pk_billing_account ON anagrafiche.billing_account USING btree (id)` |
| uq_billing_account_codice | `CREATE UNIQUE INDEX uq_billing_account_codice ON anagrafiche.billing_account USING btree (codice)` |
| uq_billing_account_id_cliente | `CREATE UNIQUE INDEX uq_billing_account_id_cliente ON anagrafiche.billing_account USING btree (id, soggetto_ruolo_id, utility_id)` |
| uq_billing_account_id_coppia | `CREATE UNIQUE INDEX uq_billing_account_id_coppia ON anagrafiche.billing_account USING btree (id, istanza_utility_id, utility_id)` |
| uq_billing_account_id_istanza_utility | `CREATE UNIQUE INDEX uq_billing_account_id_istanza_utility ON anagrafiche.billing_account USING btree (id, istanza_utility_id)` |
| uq_billing_instance_utility | `CREATE UNIQUE INDEX uq_billing_instance_utility ON anagrafiche.billing_account USING btree (istanza_utility_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_billing_account_a10_canale_origine_immutable_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_canale_origine_immutable()` |
| trg_billing_account_a10_categorie_clienti_require_attivo_566444 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'categorie_clienti', 'attivo', 'categoria_cliente_id', 'id')` |
| trg_billing_account_a10_categorie_clienti_require_attivo_566444 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'categorie_clienti', 'attivo', 'categoria_cliente_id', 'id')` |
| trg_billing_account_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_billing_account_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_billing_account_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_gen_codice()` |
| trg_billing_account_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_gen_codice()` |
| trg_billing_account_a10_guard_admin_globale_ins | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_admin_globale()` |
| trg_billing_account_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE', 'istanza_utility_id', 'E_BA_ISTANZA_IMMUTABILE', 'soggetto_ruolo_id', 'E_BA_ISTANZA_IMMUTABILE', 'utility_id', 'E_BA_ISTANZA_IMMUTABILE')` |
| trg_billing_account_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_billing_account_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_billing_account_a20_guard_soggetto_coerenza_istanza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()` |
| trg_billing_account_a20_guard_soggetto_coerenza_istanza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza()` |
| trg_billing_account_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_billing_account_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_billing_account_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_billing_account_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_billing_account_guard_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()` |
| trg_billing_account_guard_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()` |
| trg_billing_account_z90_link_ef_ins | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_link_ef()` |
| trg_billing_account_z90_require_istanza_ha_ba_dlt | AFTER | DELETE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_require_istanza_ha_ba()` |
| trg_billing_account_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('billing_account_id')` |
| trg_billing_account_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('billing_account_id')` |
| trg_billing_account_z95_guard_albero_emittente_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_albero_emittente()` |
| trg_billing_account_z95_guard_albero_emittente_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_albero_emittente()` |
| trg_billing_account_z95_guard_istanza_emittente_ins | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_istanza_emittente()` |

---
{% include-markdown "signature-core.md" %}
