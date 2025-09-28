{% include-markdown "it/dbzero/anagrafiche/manual/clienti.md" %}
# 📚 Tabella `clienti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| soggetto_ruolo_id | integer | NO |  |
| istanza_utility_id | integer | NO |  |
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
| user_insert | character varying | NO | 'CURRENT_USER'::character varying |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | 'CURRENT_USER'::character varying |
| utility_id | integer | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| pdp_id | bigint | YES |  |
| data_attivazione | date | YES |  |
| data_sospensione | date | YES |  |
| data_riattivazione | date | YES |  |
| data_chiusura | date | YES |  |
| tipo_giorni_scadenza | character | YES | 'N'::bpchar |
| numero_giorni | smallint | YES |  |
| garanzia_tipo | character | YES | 'D'::bpchar |
| garanzia_importo | numeric | YES | 0 |
| periodo | daterange | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_clienti_date_coerenti |  |
| CHECK | chk_clienti_garanzia_importo_nonneg |  |
| CHECK | chk_clienti_garanzia_tipo |  |
| CHECK | chk_clienti_numero_giorni_range |  |
| CHECK | chk_clienti_numero_giorni_uso |  |
| CHECK | chk_clienti_tipo_giorni_scadenza |  |
| FOREIGN KEY | fk_clienti_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_clienti_pdp | pdp_id |
| FOREIGN KEY | fk_iva_config | iva_id |
| FOREIGN KEY | fk_modalita_pagamento_config | modalita_pagamento_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_cliente_config | stato_cliente_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_clienti | id |

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

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_clienti_ins_upd_check_ruolo_cliente | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_ins_upd_check_ruolo_cliente()` |
| trg_clienti_ins_upd_check_ruolo_cliente | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_ins_upd_check_ruolo_cliente()` |
| trg_clienti_ins_upd_set_periodo | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_periodo()` |
| trg_clienti_ins_upd_set_periodo | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_periodo()` |
| trg_clienti_ins_upd_sync_pdp | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_pdp()` |
| trg_clienti_ins_upd_sync_pdp | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_pdp()` |
| trg_clienti_ins_upd_tx_id_managed | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_clienti_ins_upd_tx_id_managed | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_clienti_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_clienti_z90_upd_dlt_storico_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('cliente_id')` |
| trg_clienti_z90_upd_dlt_storico_generic | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('cliente_id')` |

---
{% include-markdown "signature-core.md" %}
