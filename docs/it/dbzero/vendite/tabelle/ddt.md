{% include-markdown "it/dbzero/vendite/manual/ddt.md" %}
# 📚 Tabella `ddt`

> 📝 **Descrizione**
>
> Documento di Trasporto (DDT) – vendita.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| anno | smallint | YES |  |
| serie | character varying(8) | YES |  |
| numero | character varying(20) | YES |  |
| data | date | NO | script.fn_data_operativa() |
| stato_doc_ddt_id | bigint | NO |  |
| mittente_soggetto_ruolo_id | bigint | YES |  |
| destinatario_soggetto_ruolo_id | bigint | NO |  |
| vettore_soggetto_ruolo_id | bigint | YES |  |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric(18,3) | YES |  |
| peso_netto | numeric(18,3) | YES |  |
| volume | numeric(18,3) | YES |  |
| targa | character varying(20) | YES |  |
| autista | character varying(80) | YES |  |
| data_ora_partenza | timestamp with time zone | YES |  |
| data_ora_consegna_prev | timestamp with time zone | YES |  |
| tracking_code | character varying(64) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| billing_account_id | bigint | YES |  |
| utility_id | integer | YES |  |
| valuta_id | integer | YES |  |
| emittente_fiscale_id | bigint | NO |  |
| fatturazione_immediata | boolean | NO | false |
| registro_id | bigint | YES |  |
| magazzino_id | bigint | YES |  |
| magazzino_arrivo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ddt_ba_utility_insieme |  |
| CHECK | chk_ddt_magazzino_arrivo_distinto |  |
| CHECK | chk_ddt_peso_lordo_finito |  |
| CHECK | chk_ddt_peso_netto_finito |  |
| CHECK | chk_ddt_volume_finito |  |
| FOREIGN KEY | fk_ddt_ba_cliente | billing_account_id, destinatario_soggetto_ruolo_id, utility_id |
| FOREIGN KEY | fk_ddt_magazzino | magazzino_id |
| FOREIGN KEY | fk_ddt_magazzino_arrivo | magazzino_arrivo_id |
| FOREIGN KEY | fk_ddt_registro | registro_id |
| FOREIGN KEY | fk_ddt_v_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_ddt_v_billing_account | billing_account_id |
| FOREIGN KEY | fk_ddt_v_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_ddt_v_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_ddt_v_mod_add_trasporto | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_ddt_v_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ddt_v_stato_ddt | stato_doc_ddt_id |
| FOREIGN KEY | fk_ddt_v_utility | utility_id |
| FOREIGN KEY | fk_ddt_v_valuta | valuta_id |
| FOREIGN KEY | fk_ddt_vendita_destinatario_ruolo | destinatario_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_vendita_mittente_ruolo | mittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_vendita_vettore_ruolo | vettore_soggetto_ruolo_id |
| PRIMARY KEY | pk_ddtv | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ddt_v_sorgente | `CREATE INDEX ix_ddt_v_sorgente ON vendite.ddt USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_tipo_id IS NOT NULL)` |
| ix_ddt_vendita_dest_stato_data | `CREATE INDEX ix_ddt_vendita_dest_stato_data ON vendite.ddt USING btree (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data)` |
| ix_vendite_ddt_stato_doc_ddt_id | `CREATE INDEX ix_vendite_ddt_stato_doc_ddt_id ON vendite.ddt USING btree (stato_doc_ddt_id)` |
| pk_ddtv | `CREATE UNIQUE INDEX pk_ddtv ON vendite.ddt USING btree (id)` |
| uq_ddt_v_anno_serie_numero | `CREATE UNIQUE INDEX uq_ddt_v_anno_serie_numero ON vendite.ddt USING btree (registro_id, anno, serie, numero) NULLS NOT DISTINCT WHERE (numero IS NOT NULL)` |
| uq_ddt_vendita_uid | `CREATE UNIQUE INDEX uq_ddt_vendita_uid ON vendite.ddt USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_a05_lock_fuori_bozza_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza('DDT_VENDITA', 'DRAFT', 'data', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'valuta_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'anno', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'serie', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'registro_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'causale_trasporto_id', 'E_DDT_CAUSALE_IMMUTABILE', '', 'billing_account_id', 'E_DDT_CLIENTE_IMMUTABILE', '', 'utility_id', 'E_DDT_CLIENTE_IMMUTABILE', '', 'destinatario_soggetto_ruolo_id', 'E_DDT_CLIENTE_IMMUTABILE', '', 'magazzino_id', 'E_DDT_MAGAZZINO_IMMUTABILE', '', 'magazzino_arrivo_id', 'E_DDT_MAGAZZINO_IMMUTABILE', '', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_FUORI_BOZZA', '', 'sorgente_tipo_id', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'sorgente_uid', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'mittente_soggetto_ruolo_id', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'vettore_soggetto_ruolo_id', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'aspetto_bene_id', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'modalita_addebito_trasporto_id', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'num_colli', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'peso_lordo', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'peso_netto', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'volume', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'targa', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'autista', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'data_ora_partenza', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'data_ora_consegna_prev', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'tracking_code', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO', 'meta', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO,CONSEGNATO')` |
| trg_ddt_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_ddt_id', 'config.stati_doc_ddt')` |
| trg_ddt_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_ddt_a10_aspetti_beni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id', 'id')` |
| trg_ddt_a10_aspetti_beni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id', 'id')` |
| trg_ddt_a10_causali_trasporto_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id', 'id')` |
| trg_ddt_a10_causali_trasporto_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id', 'id')` |
| trg_ddt_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('LASCIA_NULL', 'SALTA_CON_SORGENTE')` |
| trg_ddt_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_ddt_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_ddt_a10_guard_approvazione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_transizione_approvazione()` |
| trg_ddt_a10_guard_causale_emissione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_causale_emissione()` |
| trg_ddt_a10_guard_chiusura_sorgente_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_chiusura_sorgente('DDT_VENDITA', 'stato_doc_ddt_id', 'config.stati_doc_ddt')` |
| trg_ddt_a10_guard_delete_solo_bozza_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()` |
| trg_ddt_a10_guard_fatt_immediata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('DDT_VENDITA')` |
| trg_ddt_a10_guard_indirizzi_obbligatori_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_indirizzi_obbligatori()` |
| trg_ddt_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_transizione()` |
| trg_ddt_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_ddt_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_ddt_a10_modalita_addebito_trasporto_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id', 'id')` |
| trg_ddt_a10_modalita_addebito_trasporto_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id', 'id')` |
| trg_ddt_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_ddt_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_ddt_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ddt_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ddt_a10_stati_doc_ddt_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_doc_ddt_id', 'id')` |
| trg_ddt_a10_stati_doc_ddt_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_doc_ddt_id', 'id')` |
| trg_ddt_a10_v_protect_num_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_v_ddt_protect_num()` |
| trg_ddt_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_m10_guard_annullo_con_legami_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_annullo_con_legami('DDT_VENDITA', 'stato_doc_ddt_id', 'config.stati_doc_ddt')` |
| trg_ddt_m50_indirizzi_seguono_cliente_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_seguono_cliente('DDT_VENDITA')` |
| trg_ddt_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ddt_normalize()` |
| trg_ddt_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_normalize()` |
| trg_ddt_z10_default_magazzino_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ddt_default_magazzino()` |
| trg_ddt_z10_gen_numero_emesso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ddt_gen_numero_emesso()` |
| trg_ddt_z10_gen_numero_emesso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_gen_numero_emesso()` |
| trg_ddt_z10_guard_cliente_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_cliente_sorgente()` |
| trg_ddt_z10_guard_cliente_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_cliente_sorgente()` |
| trg_ddt_z10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('DDT_VENDITA', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_ddt_z10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('DDT_VENDITA', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_ddt_z10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_ddt_z10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_ddt_z10_guard_magazzino_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_magazzino()` |
| trg_ddt_z10_guard_magazzino_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_guard_magazzino()` |
| trg_ddt_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_id')` |
| trg_ddt_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_id')` |
| trg_ddt_z90_sync_canali_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |
| trg_ddt_z90_sync_canali_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |

---
{% include-markdown "signature-core.md" %}
