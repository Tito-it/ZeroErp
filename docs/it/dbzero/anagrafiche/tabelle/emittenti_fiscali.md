{% include-markdown "it/dbzero/anagrafiche/manual/emittenti_fiscali.md" %}
# 📚 Tabella `emittenti_fiscali`

> 📝 **Descrizione**
>
> Ruoli che emettono fiscalmente (gestore/reseller/brand): preferenze di numerazione, IBAN predefinito, override fiscali e branding.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying(32) | NO |  |
| attivo | boolean | NO | true |
| regime_fiscale_rf | character varying(8) | NO | 'RF01'::character varying |
| bollo_auto | boolean | YES |  |
| bollo_soglia | numeric(12,2) | YES |  |
| rounding_policy | character varying(16) | YES |  |
| brand_meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| valuta_id | integer | YES |  |
| regime_fiscale_confermato_il | timestamp with time zone | YES |  |
| regime_fiscale_confermato_da | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_emittenti_fiscali_bollo_soglia |  |
| CHECK | chk_emittenti_fiscali_bollo_soglia_finito |  |
| CHECK | chk_emittenti_fiscali_codice_forma |  |
| CHECK | chk_emittenti_fiscali_codice_non_vuoto |  |
| CHECK | chk_emittenti_fiscali_regime_conferma_coppia |  |
| CHECK | chk_emittenti_fiscali_rounding_policy |  |
| FOREIGN KEY | fk_emittenti_fiscali_regimi_fiscali | regime_fiscale_rf |
| FOREIGN KEY | fk_emittenti_fiscali_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_emittf | id |
| UNIQUE | uq:codice | codice |
| UNIQUE | uq_emittenti_fiscali_ruolo | soggetto_ruolo_id |
| UNIQUE | uq_emittenti_fiscali_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_emittenti_fiscali_attivo | `CREATE INDEX ix_emittenti_fiscali_attivo ON anagrafiche.emittenti_fiscali USING btree (attivo)` |
| ix_emittenti_fiscali_codice_trgm | `CREATE INDEX ix_emittenti_fiscali_codice_trgm ON anagrafiche.emittenti_fiscali USING gin (codice gin_trgm_ops)` |
| pk_emittf | `CREATE UNIQUE INDEX pk_emittf ON anagrafiche.emittenti_fiscali USING btree (id)` |
| uq:codice | `CREATE UNIQUE INDEX "uq:codice" ON anagrafiche.emittenti_fiscali USING btree (codice)` |
| uq_emittenti_fiscali_ruolo | `CREATE UNIQUE INDEX uq_emittenti_fiscali_ruolo ON anagrafiche.emittenti_fiscali USING btree (soggetto_ruolo_id)` |
| uq_emittenti_fiscali_uid | `CREATE UNIQUE INDEX uq_emittenti_fiscali_uid ON anagrafiche.emittenti_fiscali USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittenti_fiscali_a05_guard_codice_forma_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma()` |
| trg_emittenti_fiscali_a05_guard_codice_forma_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma()` |
| trg_emittenti_fiscali_a10_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'assets', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_contratti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_default_bootstrap_ins | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_bootstrap()` |
| trg_emittenti_fiscali_a10_delete_block_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_emittenti_fiscali_a10_documenti_generati_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'documenti_generati', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_email_log_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_log', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_email_outbox_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_outbox', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_emittenti_fiscali_billing_acco_b98811 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'emittenti_fiscali_billing_account', 'emittente_soggetto_ruolo_id', 'soggetto_ruolo_id', 'attivo')` |
| trg_emittenti_fiscali_a10_emittenti_fiscali_utilities_bl_fafe8a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'emittenti_fiscali_utilities', 'emittente_soggetto_ruolo_id', 'soggetto_ruolo_id', 'attivo')` |
| trg_emittenti_fiscali_a10_guard_regime_conferma_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma()` |
| trg_emittenti_fiscali_a10_guard_regime_conferma_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma()` |
| trg_emittenti_fiscali_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE')` |
| trg_emittenti_fiscali_a10_magazzini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'magazzini', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_offerte_commerciali_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_parameter_overrides_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'parameter_overrides', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_pratiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'pratiche', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_preventivi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_resi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_soggetti_titoli_iva_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_template_asset_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'template_asset', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_template_documenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'template_documenti', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_user_emittente_attivo_block_de_78b189 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'user_emittente_attivo', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_user_emittenti_fiscali_block_d_f876e4 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'user_emittenti_fiscali', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a10_workflow_definizioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'workflow_definizioni', 'emittente_fiscale_id', 'id', 'attivo')` |
| trg_emittenti_fiscali_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_emittenti_fiscali_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_emittenti_fiscali_a20_regime_conferma_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_regime_conferma()` |
| trg_emittenti_fiscali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_emittenti_fiscali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_emittenti_fiscali_guard_ruolo_emi_fis_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis()` |
| trg_emittenti_fiscali_guard_ruolo_emi_fis_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis()` |
| trg_emittenti_fiscali_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()` |
| trg_emittenti_fiscali_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()` |
| trg_emittenti_fiscali_z90_provision_registri_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_emittenti_fiscali_provision_registri()` |
| trg_emittenti_fiscali_z90_provision_registri_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_emittenti_fiscali_provision_registri()` |
| trg_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('emittenti_fiscali_id')` |
| trg_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('emittenti_fiscali_id')` |

---
{% include-markdown "signature-core.md" %}
