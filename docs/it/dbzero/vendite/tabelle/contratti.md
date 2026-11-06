{% include-markdown "it/dbzero/vendite/manual/contratti.md" %}
# 📚 Tabella `contratti`

> 📝 **Descrizione**
>
> Contratti commerciali; versione attiva per BA/istanza/utility per ambito; numerazione dedicata

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| numero | character varying(30) | NO |  |
| billing_account_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| ambito | character varying(24) | YES | 'COMMODITY'::character varying |
| valido_dal | date | NO | script.fn_data_operativa() |
| valido_al | date | YES |  |
| parent_contratto_id | bigint | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| stato_doc_contratto_id | bigint | NO |  |
| data | date | NO | script.fn_data_operativa() |
| uid | uuid | NO | uuidv7() |
| listino_id | bigint | YES |  |
| tipo_variazione_globale | character varying(16) | YES |  |
| valore_variazione_globale | numeric(10,4) | YES |  |
| categoria_cliente_id_snapshot | smallint | YES |  |
| tx_id | uuid | YES |  |
| validita | daterange | NO |  |
| listino_versione_id | bigint | YES |  |
| is_abortito_snapshot | boolean | NO | false |
| offerta_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| emittente_fiscale_id | bigint | NO |  |
| valuta_id | integer | YES |  |
| is_draft_snapshot | boolean | NO | false |
| partecipa_overlap_snapshot | boolean | YES |  |
| fatturazione_immediata | boolean | NO | false |
| codice_cig | character varying(15) | YES |  |
| codice_cup | character varying(15) | YES |  |
| codice_commessa | character varying(100) | YES |  |
| generazione_canone | character varying(32) | NO | 'INIZIO_PERIODO'::character varying |
| mese_partenza_canone | smallint | NO | 1 |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_contratti_generazione_canone |  |
| CHECK | chk_contratti_mese_partenza_canone |  |
| CHECK | chk_contratti_tipo_variazione_globale |  |
| CHECK | chk_contratti_validita |  |
| CHECK | chk_contratti_valore_variazione_globale_finito |  |
| FOREIGN KEY | fk_contratti_ba_coppia | billing_account_id, istanza_utility_id, utility_id |
| FOREIGN KEY | fk_contratti_billing_account | billing_account_id |
| FOREIGN KEY | fk_contratti_categoria_cliente_snapshot | categoria_cliente_id_snapshot |
| FOREIGN KEY | fk_contratti_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_contratti_istanza | istanza_utility_id |
| FOREIGN KEY | fk_contratti_listino | listino_id |
| FOREIGN KEY | fk_contratti_listino_versione | listino_versione_id |
| FOREIGN KEY | fk_contratti_offerta | offerta_id |
| FOREIGN KEY | fk_contratti_parent | parent_contratto_id |
| FOREIGN KEY | fk_contratti_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_contratti_utility | utility_id |
| FOREIGN KEY | fk_contratti_valuta | valuta_id |
| FOREIGN KEY | fk_v_contratti_stato_ddt | stato_doc_contratto_id |
| PRIMARY KEY | pk_contratti | id |
| UNIQUE | uq_contratti_numero | numero |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_contratti_no_overlap | `CREATE INDEX ex_contratti_no_overlap ON vendite.contratti USING gist (billing_account_id, istanza_utility_id, utility_id, ambito, validita) WHERE partecipa_overlap_snapshot` |
| ix_contratti_ambito | `CREATE INDEX ix_contratti_ambito ON vendite.contratti USING btree (ambito)` |
| ix_contratti_ba_istanza | `CREATE INDEX ix_contratti_ba_istanza ON vendite.contratti USING btree (billing_account_id, istanza_utility_id)` |
| ix_contratti_categoria_cliente_snapshot | `CREATE INDEX ix_contratti_categoria_cliente_snapshot ON vendite.contratti USING btree (categoria_cliente_id_snapshot)` |
| ix_contratti_id_text | `CREATE INDEX ix_contratti_id_text ON vendite.contratti USING btree (((id)::text))` |
| ix_contratti_listino_versione | `CREATE INDEX ix_contratti_listino_versione ON vendite.contratti USING btree (listino_versione_id)` |
| pk_contratti | `CREATE UNIQUE INDEX pk_contratti ON vendite.contratti USING btree (id)` |
| uq_contratti_numero | `CREATE UNIQUE INDEX uq_contratti_numero ON vendite.contratti USING btree (numero)` |
| uq_contratti_offerta_id | `CREATE UNIQUE INDEX uq_contratti_offerta_id ON vendite.contratti USING btree (offerta_id) WHERE ((offerta_id IS NOT NULL) AND (NOT is_abortito_snapshot))` |
| uq_contratti_uid | `CREATE UNIQUE INDEX uq_contratti_uid ON vendite.contratti USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contratti_a05_lock_fuori_bozza_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza('CONTRATTO', 'DRAFT', 'data', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'valuta_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'billing_account_id', 'E_DOC_CLIENTE_FUORI_BOZZA', '', 'istanza_utility_id', 'E_DOC_CLIENTE_FUORI_BOZZA', '', 'utility_id', 'E_DOC_UTILITY_IMMUTABILE', '-', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_IMMUTABILE', '-', 'listino_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'listino_versione_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'tipo_variazione_globale', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'valore_variazione_globale', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'ambito', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'valido_dal', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'generazione_canone', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'mese_partenza_canone', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'parent_contratto_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'categoria_cliente_id_snapshot', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'offerta_id', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'sorgente_tipo_id', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'sorgente_uid', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'valido_al', 'E_DOC_CHIUSO', 'ATTIVO', 'codice_cig', 'E_DOC_CHIUSO', 'ATTIVO', 'codice_cup', 'E_DOC_CHIUSO', 'ATTIVO', 'codice_commessa', 'E_DOC_CHIUSO', 'ATTIVO', 'meta', 'E_DOC_CHIUSO', 'ATTIVO')` |
| trg_contratti_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_contratto_id', 'config.stati_doc_contratti')` |
| trg_contratti_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_contratti_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_contratti_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_contratti_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_contratti_a10_default_valuta_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_default_valuta()` |
| trg_contratti_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_contratti_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_contratti_a10_freeze_listino_versione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_freeze_listino_versione()` |
| trg_contratti_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_gen_codice()` |
| trg_contratti_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_gen_codice()` |
| trg_contratti_a10_guard_chiusura_sorgente_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_chiusura_sorgente('CONTRATTO', 'stato_doc_contratto_id', 'config.stati_doc_contratti')` |
| trg_contratti_a10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Contratto', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_contratti_a10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Contratto', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_contratti_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_contratti_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_contratti_a10_guard_fatt_immediata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('CONTRATTO')` |
| trg_contratti_a10_guard_listino_con_righe_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_listino_con_righe('CONTRATTO')` |
| trg_contratti_a10_guard_listino_documento_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_listino_documento('CONTRATTO')` |
| trg_contratti_a10_guard_listino_documento_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_listino_documento('CONTRATTO')` |
| trg_contratti_a10_guard_transizione_stato_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_guard_transizione_stato()` |
| trg_contratti_a10_listini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_contratti_a10_listini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_contratti_a10_listini_versioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_contratti_a10_listini_versioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_contratti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'E_CODICE_NON_MODIFICABILE')` |
| trg_contratti_a10_set_categoria_cliente_snapshot_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()` |
| trg_contratti_a10_set_categoria_cliente_snapshot_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()` |
| trg_contratti_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_contratti_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_contratti_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_contratti_a10_stati_doc_contratti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_doc_contratto_id', 'id')` |
| trg_contratti_a10_stati_doc_contratti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_doc_contratto_id', 'id')` |
| trg_contratti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contratti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contratti_m10_guard_annullo_con_legami_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_annullo_con_legami('CONTRATTO', 'stato_doc_contratto_id', 'config.stati_doc_contratti')` |
| trg_contratti_m50_fornitura_segue_cliente_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_fornitura_segue_cliente('CONTRATTO')` |
| trg_contratti_m50_indirizzi_seguono_cliente_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_seguono_cliente('CONTRATTO')` |
| trg_contratti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_normalize()` |
| trg_contratti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_normalize()` |
| trg_contratti_z90_snapshot_da_stato_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_snapshot_da_stato('stato_doc_contratto_id', 'config.stati_doc_contratti', 'is_abortito_snapshot', 'is_abortito', 'is_draft_snapshot', 'is_bozza')` |
| trg_contratti_z90_snapshot_da_stato_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_snapshot_da_stato('stato_doc_contratto_id', 'config.stati_doc_contratti', 'is_abortito_snapshot', 'is_abortito', 'is_draft_snapshot', 'is_bozza')` |
| trg_contratti_z90_snapshot_precontrattuali_ins | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_snapshot_precontrattuali()` |
| trg_contratti_z90_sync_canali_ins | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |

---
{% include-markdown "signature-core.md" %}
