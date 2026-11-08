{% include-markdown "it/dbzero/vendite/manual/resi.md" %}
# 📚 Tabella `resi`

> 📝 **Descrizione**
>
> Testata documento reso di vendita (brief-db-resi-vendita §3). Sorgente data-driven DDT_VENDITA; denormalizzati ereditati dal DDT origine (trgfn_resi_normalize); emittente NOT NULL; numero a CONFERMA. rev 2026-07-13.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| anno | smallint | YES |  |
| numero | character varying(32) | YES |  |
| data | date | NO | script.fn_data_operativa() |
| stato_doc_reso_id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | uuid | YES |  |
| destinatario_soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | bigint | YES |  |
| utility_id | integer | YES |  |
| valuta_id | integer | YES |  |
| emittente_fiscale_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| registro_id | bigint | YES |  |
| magazzino_id | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_resi_ba_utility_insieme |  |
| CHECK | chk_resi_sorgente_forma |  |
| FOREIGN KEY | fk_resi_ba_cliente | billing_account_id, destinatario_soggetto_ruolo_id, utility_id |
| FOREIGN KEY | fk_resi_billing_account | billing_account_id |
| FOREIGN KEY | fk_resi_destinatario_ruolo | destinatario_soggetto_ruolo_id |
| FOREIGN KEY | fk_resi_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_resi_magazzino | magazzino_id |
| FOREIGN KEY | fk_resi_registro | registro_id |
| FOREIGN KEY | fk_resi_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_resi_stato | stato_doc_reso_id |
| FOREIGN KEY | fk_resi_utility | utility_id |
| FOREIGN KEY | fk_resi_valuta | valuta_id |
| PRIMARY KEY | pk_resi | id |
| UNIQUE | uq_resi_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_sorgente_id | `CREATE INDEX ix_resi_sorgente_id ON vendite.resi USING btree (sorgente_tipo_id, sorgente_id) WHERE (sorgente_id IS NOT NULL)` |
| ix_resi_stato | `CREATE INDEX ix_resi_stato ON vendite.resi USING btree (stato_doc_reso_id)` |
| pk_resi | `CREATE UNIQUE INDEX pk_resi ON vendite.resi USING btree (id)` |
| uq_resi_anno_numero | `CREATE UNIQUE INDEX uq_resi_anno_numero ON vendite.resi USING btree (registro_id, anno, numero) NULLS NOT DISTINCT WHERE (numero IS NOT NULL)` |
| uq_resi_uid | `CREATE UNIQUE INDEX uq_resi_uid ON vendite.resi USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_a05_lock_fuori_bozza_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza('RESO_VENDITA', 'DRAFT', 'data', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'valuta_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'anno', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'registro_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'magazzino_id', 'E_RESO_MAGAZZINO_IMMUTABILE', '', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_FUORI_BOZZA', '', 'sorgente_tipo_id', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'sorgente_uid', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'sorgente_id', 'E_DOC_SORGENTE_FUORI_BOZZA', '', 'meta', 'E_DOC_CHIUSO', 'CONFERMATO')` |
| trg_resi_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_reso_id', 'config.stati_doc_reso')` |
| trg_resi_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_resi_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_resi_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_resi_a10_gen_numero_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_gen_numero()` |
| trg_resi_a10_gen_numero_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_gen_numero()` |
| trg_resi_a10_guard_ddt_consegnato_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_guard_ddt_consegnato()` |
| trg_resi_a10_guard_delete_solo_bozza_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()` |
| trg_resi_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_resi_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_resi_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_guard_transizione()` |
| trg_resi_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_resi_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_resi_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_resi_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_resi_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_resi_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_resi_a10_stati_doc_reso_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_reso', 'attivo', 'stato_doc_reso_id', 'id')` |
| trg_resi_a10_stati_doc_reso_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_reso', 'attivo', 'stato_doc_reso_id', 'id')` |
| trg_resi_a10_v_protect_num_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_v_resi_protect_num()` |
| trg_resi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_normalize()` |
| trg_resi_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_normalize()` |
| trg_resi_z10_default_magazzino_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_default_magazzino()` |
| trg_resi_z10_guard_cliente_ddt_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_guard_cliente_ddt()` |
| trg_resi_z10_guard_cliente_ddt_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_guard_cliente_ddt()` |
| trg_resi_z10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Reso', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_resi_z10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Reso', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_resi_z10_guard_magazzino_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_guard_magazzino()` |
| trg_resi_z10_guard_magazzino_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_guard_magazzino()` |
| trg_resi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_id')` |
| trg_resi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_id')` |
| trg_vendite_resi_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
