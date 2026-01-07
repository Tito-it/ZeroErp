{% include-markdown "it/dbzero/anagrafiche/manual/clienti.md" %}
# 📚 Tabella `clienti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| tipo_gg_scadenza_ft | character | NO | 'N'::bpchar |
| nr_giorni_scadenza | integer | NO | 0 |
| modalita_pagamento_id | integer | YES |  |
| cliente_pa | character | NO | 'N'::bpchar |
| codice_cig | character varying | YES |  |
| codice_cup | character varying | YES |  |
| codice_commessa | character varying | YES |  |
| split_payment | character | NO | 'N'::bpchar |
| codice_cliente_importato | character varying | YES |  |
| stato_cliente_id | integer | NO |  |
| iva_id | integer | NO |  |
| servizio_da_fatturare | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| utility_id | integer | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| pdp_id | bigint | YES |  |
| data_attivazione | date | YES |  |
| data_sospensione | date | YES |  |
| data_riattivazione | date | YES |  |
| data_chiusura | date | YES |  |
| garanzia_tipo | character | YES | 'D'::bpchar |
| garanzia_importo | numeric | YES | 0 |
| periodo | daterange | YES |  |
| termine_pagamento_id | bigint | YES |  |
| billing_account_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_clienti_date_coerenti |  |
| CHECK | chk_clienti_garanzia_importo_nonneg |  |
| CHECK | chk_clienti_garanzia_tipo |  |
| FOREIGN KEY | fk_clienti_billing_account | billing_account_id, istanza_utility_id |
| FOREIGN KEY | fk_clienti_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_clienti_pdp | pdp_id |
| FOREIGN KEY | fk_clienti_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_iva_config | iva_id |
| FOREIGN KEY | fk_modalita_pagamento_config | modalita_pagamento_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_cliente_config | stato_cliente_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_clienti | id |
| UNIQUE | uq_clienti_istanza_utility | istanza_utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_clienti_no_overlap_stesso_pdp | `CREATE INDEX ex_clienti_no_overlap_stesso_pdp ON anagrafiche.clienti USING gist (pdp_id, periodo) WHERE ((pdp_id IS NOT NULL) AND (periodo IS NOT NULL))` |
| ix_anagrafiche_clienti_istanza_id | `CREATE INDEX ix_anagrafiche_clienti_istanza_id ON anagrafiche.clienti USING btree (istanza_utility_id)` |
| ix_anagrafiche_clienti_iva_id | `CREATE INDEX ix_anagrafiche_clienti_iva_id ON anagrafiche.clienti USING btree (iva_id)` |
| ix_anagrafiche_clienti_modalita_pagamento_id | `CREATE INDEX ix_anagrafiche_clienti_modalita_pagamento_id ON anagrafiche.clienti USING btree (modalita_pagamento_id)` |
| ix_anagrafiche_clienti_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_clienti_soggetto_ruolo_id ON anagrafiche.clienti USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_clienti_stato_cliente_id | `CREATE INDEX ix_anagrafiche_clienti_stato_cliente_id ON anagrafiche.clienti USING btree (stato_cliente_id)` |
| ix_cliente_utility | `CREATE INDEX ix_cliente_utility ON anagrafiche.clienti USING btree (utility_id)` |
| ix_clienti_cd_importato | `CREATE INDEX ix_clienti_cd_importato ON anagrafiche.clienti USING btree (codice_cliente_importato)` |
| ix_clienti_pdp_id | `CREATE INDEX ix_clienti_pdp_id ON anagrafiche.clienti USING btree (pdp_id)` |
| pk_clienti | `CREATE UNIQUE INDEX pk_clienti ON anagrafiche.clienti USING btree (id)` |
| uq_clienti_istanza_utility | `CREATE UNIQUE INDEX uq_clienti_istanza_utility ON anagrafiche.clienti USING btree (istanza_utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_clienti_a20_sync_stato_pdp_aft_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()` |
| trg_clienti_a20_sync_stato_pdp_aft_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()` |
| trg_clienti_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_clienti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_clienti_guard_ruolo_cliente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_ruolo_cliente()` |
| trg_clienti_guard_ruolo_cliente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_ruolo_cliente()` |
| trg_clienti_set_periodo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_periodo()` |
| trg_clienti_set_periodo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_periodo()` |
| trg_clienti_sync_pdp_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_pdp()` |
| trg_clienti_sync_pdp_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_pdp()` |
| trg_clienti_sync_utility_from_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()` |
| trg_clienti_sync_utility_from_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()` |
| trg_clienti_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_clienti_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_clienti_z10_set_parent_istanza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()` |
| trg_clienti_z10_set_parent_istanza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()` |
| trg_clienti_z90_storico_generic_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('cliente_id')` |
| trg_clienti_z90_storico_generic_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('cliente_id')` |
| trg_clienti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('clienti_id')` |
| trg_clienti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('clienti_id')` |

---
{% include-markdown "signature-core.md" %}
