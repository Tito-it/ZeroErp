{% include-markdown "it/dbzero/vendite/manual/ordini.md" %}
# 📚 Tabella `ordini`

> 📝 **Descrizione**
>
> Ordini di vendita (testata) con campi già utili alla futura emissione di DDT.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| serie | character varying(8) | YES |  |
| numero | character varying(20) | YES |  |
| anno | smallint | YES |  |
| data | date | NO | script.fn_data_operativa() |
| stato_doc_ordine_id | bigint | NO |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric(18,8) | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| imponibile_tot | numeric(18,6) | YES |  |
| sconto_tot | numeric(18,6) | YES |  |
| iva_tot | numeric(18,6) | YES |  |
| totale_doc | numeric(18,6) | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| termine_pagamento_id | bigint | YES |  |
| fatturazione_trigger | character varying | NO |  |
| canale_origine | config.canale_origine | NO | 'ADMIN'::config.canale_origine |
| utility_id | integer | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| agente_soggetto_ruolo_id | bigint | YES |  |
| documento_origine_tipo | character varying(50) | YES |  |
| documento_origine_id | bigint | YES |  |
| fatturazione_immediata | boolean | NO | false |
| registro_id | bigint | YES |  |
| is_abortito_snapshot | boolean | NO | false |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_documento_origine_copres |  |
| CHECK | chk_ordini_fatturazione_trigger |  |
| CHECK | chk_ordini_imponibile_tot_finito |  |
| CHECK | chk_ordini_iva_tot_finito |  |
| CHECK | chk_ordini_sconto_tot_finito |  |
| CHECK | chk_ordini_tasso_cambio_finito |  |
| CHECK | chk_ordini_totale_doc_finito |  |
| FOREIGN KEY | fk_ordini_ba_cliente | billing_account_id, soggetto_ruolo_id, utility_id |
| FOREIGN KEY | fk_ordini_documento_origine_tipo_sorgenti | documento_origine_tipo |
| FOREIGN KEY | fk_ordini_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_ordini_registro | registro_id |
| FOREIGN KEY | fk_ordini_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_ordini_v_agente_ruolo | agente_soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_v_billing_account | billing_account_id |
| FOREIGN KEY | fk_ordini_v_cliente_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_v_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_ordini_v_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ordini_v_stato_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordini_v_utility | utility_id |
| FOREIGN KEY | fk_ordini_v_valute | valuta_id |
| PRIMARY KEY | pk_ordini | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_documento_origine | `CREATE INDEX ix_ordini_documento_origine ON vendite.ordini USING btree (documento_origine_tipo, documento_origine_id) WHERE (documento_origine_id IS NOT NULL)` |
| ix_ordini_emittente_fiscale_id | `CREATE INDEX ix_ordini_emittente_fiscale_id ON vendite.ordini USING btree (emittente_fiscale_id)` |
| ix_ordini_id_text | `CREATE INDEX ix_ordini_id_text ON vendite.ordini USING btree (((id)::text))` |
| ix_ordini_v_cliente_statoid_data | `CREATE INDEX ix_ordini_v_cliente_statoid_data ON vendite.ordini USING btree (soggetto_ruolo_id, stato_doc_ordine_id, data)` |
| ix_vendite_ordini_stato_doc_ordine_id | `CREATE INDEX ix_vendite_ordini_stato_doc_ordine_id ON vendite.ordini USING btree (stato_doc_ordine_id)` |
| pk_ordini | `CREATE UNIQUE INDEX pk_ordini ON vendite.ordini USING btree (id)` |
| uq_ordini_v_anno_serie_numero | `CREATE UNIQUE INDEX uq_ordini_v_anno_serie_numero ON vendite.ordini USING btree (registro_id, anno, serie, numero) NULLS NOT DISTINCT WHERE (numero IS NOT NULL)` |
| uq_ordini_v_documento_origine_offerta | `CREATE UNIQUE INDEX uq_ordini_v_documento_origine_offerta ON vendite.ordini USING btree (documento_origine_tipo, documento_origine_id) WHERE (((documento_origine_tipo)::text = 'OFFERTA_COMMERCIALE'::text) AND (NOT is_abortito_snapshot))` |
| uq_ordini_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_v_sorgente_fk ON vendite.ordini USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |
| uq_ordini_v_uid | `CREATE UNIQUE INDEX uq_ordini_v_uid ON vendite.ordini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_a05_lock_fuori_bozza_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza('ORDINE_VENDITA', 'DRAFT', 'data', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'valuta_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'tasso_cambio', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'anno', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'serie', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'registro_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'utility_id', 'E_DOC_CLIENTE_FUORI_BOZZA', '', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_FUORI_BOZZA', '', 'modalita_pagamento_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'termine_pagamento_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'agente_soggetto_ruolo_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'fatturazione_trigger', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'sorgente_tipo_id', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'sorgente_uid', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'documento_origine_tipo', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'documento_origine_id', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'meta', 'E_DOC_CHIUSO', 'CONFERMATO,PARZIALMENTE_EVASO,ALLOCATO,SPEDITO,CONSEGNATO,EVASO')` |
| trg_ordini_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_ordine_id', 'config.stati_doc_ordini')` |
| trg_ordini_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_ordini_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_ordini_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_ordini_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_ordini_a10_gen_numero_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_gen_numero()` |
| trg_ordini_a10_guard_chiusura_sorgente_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_chiusura_sorgente('ORDINE_VENDITA', 'stato_doc_ordine_id', 'config.stati_doc_ordini')` |
| trg_ordini_a10_guard_data_vs_consegne_righe_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_testata_guard_data_consegna_righe('ORDINE_VENDITA')` |
| trg_ordini_a10_guard_delete_solo_bozza_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()` |
| trg_ordini_a10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Ordine', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_ordini_a10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Ordine', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_ordini_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_ordini_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_ordini_a10_guard_fatt_immediata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('ORDINE_VENDITA')` |
| trg_ordini_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_guard_transizione()` |
| trg_ordini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('billing_account_id', 'E_ORD_CLIENTE_IMMUTABILE', 'numero', 'E_CODICE_NON_MODIFICABILE', 'soggetto_ruolo_id', 'E_ORD_CLIENTE_IMMUTABILE')` |
| trg_ordini_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_ordini_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_ordini_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_ordini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_m10_guard_annullo_con_legami_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_annullo_con_legami('ORDINE_VENDITA', 'stato_doc_ordine_id', 'config.stati_doc_ordini')` |
| trg_ordini_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_normalize()` |
| trg_ordini_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_normalize()` |
| trg_ordini_z90_snapshot_da_stato_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_snapshot_da_stato('stato_doc_ordine_id', 'config.stati_doc_ordini', 'is_abortito_snapshot', 'is_abortito')` |
| trg_ordini_z90_snapshot_da_stato_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_snapshot_da_stato('stato_doc_ordine_id', 'config.stati_doc_ordini', 'is_abortito_snapshot', 'is_abortito')` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |
| trg_vendite_ordini_a10_canale_origine_immutable_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_canale_origine_immutable()` |
| trg_vendite_ordini_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
