{% include-markdown "it/dbzero/anagrafiche/manual/emittenti_fiscali.md" %}
# 📚 Tabella `emittenti_fiscali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| regime_fiscale_rf | character varying | YES |  |
| esigibilita_iva_default | character | YES |  |
| split_payment_default | boolean | YES |  |
| bollo_auto | boolean | YES |  |
| bollo_soglia | numeric | YES |  |
| rounding_policy | character varying | YES |  |
| brand_meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_emittenti_fiscali_bollo_soglia |  |
| CHECK | chk_emittenti_fiscali_codice_non_vuoto |  |
| CHECK | chk_emittenti_fiscali_esigibilita |  |
| FOREIGN KEY | fk_emittenti_fiscali_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_emittf | id |
| UNIQUE | uq:codice | codice |
| UNIQUE | uq_emittenti_fiscali_ruolo | soggetto_ruolo_id |
| UNIQUE | uq_emittenti_fiscali_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_emittenti_fiscali_attivo | `CREATE INDEX ix_emittenti_fiscali_attivo ON anagrafiche.emittenti_fiscali USING btree (attivo)` |
| pk_emittf | `CREATE UNIQUE INDEX pk_emittf ON anagrafiche.emittenti_fiscali USING btree (id)` |
| uq:codice | `CREATE UNIQUE INDEX "uq:codice" ON anagrafiche.emittenti_fiscali USING btree (codice)` |
| uq_emittenti_fiscali_ruolo | `CREATE UNIQUE INDEX uq_emittenti_fiscali_ruolo ON anagrafiche.emittenti_fiscali USING btree (soggetto_ruolo_id)` |
| uq_emittenti_fiscali_uid | `CREATE UNIQUE INDEX uq_emittenti_fiscali_uid ON anagrafiche.emittenti_fiscali USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittenti_fiscali_a10_default_bootstrap_ins | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_bootstrap()` |
| trg_emittenti_fiscali_a10_delete_block_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_emittenti_fiscali_a10_emittenti_fiscali_utilities_bl_fafe8a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'emittenti_fiscali_utilities', 'emittente_soggetto_ruolo_id', 'id')` |
| trg_emittenti_fiscali_a10_guard_attivo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_attivo()` |
| trg_emittenti_fiscali_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')` |
| trg_emittenti_fiscali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_emittenti_fiscali_guard_ruolo_emi_fis_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis()` |
| trg_emittenti_fiscali_guard_ruolo_emi_fis_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis()` |
| trg_emittenti_fiscali_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()` |
| trg_emittenti_fiscali_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_normalize()` |
| trg_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('emittenti_fiscali_id')` |
| trg_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('emittenti_fiscali_id')` |

---
{% include-markdown "signature-core.md" %}
