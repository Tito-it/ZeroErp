{% include-markdown "it/dbzero/anagrafiche/manual/clienti.md" %}
# 📚 Tabella `clienti`

> 📝 **Descrizione**
>
> Tabella anagrafica generale clienti per tutte le utilities

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| modalita_pagamento_id | integer | YES |  |
| codice_cliente_importato | character varying(30) | YES |  |
| stato_cliente_id | integer | NO |  |
| servizio_da_fatturare | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| utility_id | integer | NO |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| pdp_id | bigint | YES |  |
| data_attivazione | date | YES |  |
| data_sospensione | date | YES |  |
| data_riattivazione | date | YES |  |
| data_chiusura | date | YES |  |
| garanzia_tipo | character(1) | YES | 'D'::bpchar |
| garanzia_importo | numeric(12,2) | YES | 0 |
| periodo | daterange | YES |  |
| termine_pagamento_id | bigint | YES |  |
| billing_account_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_clienti_date_coerenti |  |
| CHECK | chk_clienti_garanzia_importo_finito |  |
| CHECK | chk_clienti_garanzia_importo_nonneg |  |
| CHECK | chk_clienti_garanzia_tipo |  |
| FOREIGN KEY | fk_clienti_ba_cliente | billing_account_id, soggetto_ruolo_id, utility_id |
| FOREIGN KEY | fk_clienti_billing_account | billing_account_id, istanza_utility_id |
| FOREIGN KEY | fk_clienti_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_clienti_pdp | pdp_id |
| FOREIGN KEY | fk_clienti_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_modalita_pagamento_config | modalita_pagamento_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_cliente_config | stato_cliente_id |
| FOREIGN KEY | fk_utilities_config | utility_id |
| PRIMARY KEY | pk_clienti | id |
| UNIQUE | uq_clienti_billing_account | billing_account_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_clienti_no_overlap_stesso_pdp | `CREATE INDEX ex_clienti_no_overlap_stesso_pdp ON anagrafiche.clienti USING gist (pdp_id, periodo) WHERE ((pdp_id IS NOT NULL) AND (periodo IS NOT NULL))` |
| ix_anagrafiche_clienti_istanza_utility_id | `CREATE INDEX ix_anagrafiche_clienti_istanza_utility_id ON anagrafiche.clienti USING btree (istanza_utility_id)` |
| ix_anagrafiche_clienti_modalita_pagamento_id | `CREATE INDEX ix_anagrafiche_clienti_modalita_pagamento_id ON anagrafiche.clienti USING btree (modalita_pagamento_id)` |
| ix_anagrafiche_clienti_pdp_id | `CREATE INDEX ix_anagrafiche_clienti_pdp_id ON anagrafiche.clienti USING btree (pdp_id)` |
| ix_anagrafiche_clienti_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_clienti_soggetto_ruolo_id ON anagrafiche.clienti USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_clienti_stato_cliente_id | `CREATE INDEX ix_anagrafiche_clienti_stato_cliente_id ON anagrafiche.clienti USING btree (stato_cliente_id)` |
| ix_anagrafiche_clienti_utility_id | `CREATE INDEX ix_anagrafiche_clienti_utility_id ON anagrafiche.clienti USING btree (utility_id)` |
| ix_clienti_cd_importato | `CREATE INDEX ix_clienti_cd_importato ON anagrafiche.clienti USING btree (codice_cliente_importato)` |
| pk_clienti | `CREATE UNIQUE INDEX pk_clienti ON anagrafiche.clienti USING btree (id)` |
| uq_clienti_billing_account | `CREATE UNIQUE INDEX uq_clienti_billing_account ON anagrafiche.clienti USING btree (billing_account_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_clienti_a10_delete_block_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_clienti_a10_guard_stato_date_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_stato_date()` |
| trg_clienti_a10_guard_stato_date_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_stato_date()` |
| trg_clienti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('billing_account_id', 'E_CLIENTE_FORNITURA_IMMUTABILE', 'istanza_utility_id', 'E_CLIENTE_FORNITURA_IMMUTABILE', 'soggetto_ruolo_id', 'E_CLIENTE_FORNITURA_IMMUTABILE', 'utility_id', 'E_CLIENTE_FORNITURA_IMMUTABILE')` |
| trg_clienti_a10_pdp_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'pdp', 'attivo', 'pdp_id', 'id')` |
| trg_clienti_a10_pdp_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'pdp', 'attivo', 'pdp_id', 'id')` |
| trg_clienti_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_clienti_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_clienti_a20_sync_stato_pdp_aft_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()` |
| trg_clienti_a20_sync_stato_pdp_aft_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()` |
| trg_clienti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_clienti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_clienti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_clienti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_clienti_guard_ruolo_cliente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_ruolo_cliente()` |
| trg_clienti_guard_ruolo_cliente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_ruolo_cliente()` |
| trg_clienti_set_periodo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_periodo()` |
| trg_clienti_set_periodo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_periodo()` |
| trg_clienti_sync_pdp_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_pdp()` |
| trg_clienti_sync_pdp_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_pdp()` |
| trg_clienti_sync_utility_from_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()` |
| trg_clienti_sync_utility_from_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()` |
| trg_clienti_z10_set_parent_istanza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()` |
| trg_clienti_z10_set_parent_istanza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()` |
| trg_clienti_z90_guard_chiave_unica_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_chiave_unica()` |
| trg_clienti_z90_guard_chiave_unica_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_chiave_unica()` |
| trg_clienti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('cliente_id')` |
| trg_clienti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('cliente_id')` |

---
{% include-markdown "signature-core.md" %}
