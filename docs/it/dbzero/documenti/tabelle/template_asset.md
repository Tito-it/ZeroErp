{% include-markdown "it/dbzero/documenti/manual/template_asset.md" %}
# 📚 Tabella `template_asset`

> 📝 **Descrizione**
>
> Catalogo degli asset documentali riusabili per emittente fiscale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(120) | NO |  |
| codice_interno | character varying(120) | NO |  |
| descrizione | text | NO |  |
| asset_tipo_id | bigint | NO |  |
| mime_type | character varying(120) | NO |  |
| file_name | text | NO |  |
| file_size_bytes | bigint | NO |  |
| storage_key | text | NO |  |
| sha256 | character varying(64) | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| valido_dal | date | NO | script.fn_data_operativa() |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_template_asset_codice_interno_non_vuoto |  |
| CHECK | chk_template_asset_codice_non_vuoto |  |
| CHECK | chk_template_asset_descrizione_non_vuota |  |
| CHECK | chk_template_asset_file_name_non_vuoto |  |
| CHECK | chk_template_asset_file_size_pos |  |
| CHECK | chk_template_asset_mime_type_non_vuoto |  |
| CHECK | chk_template_asset_sha256_len |  |
| CHECK | chk_template_asset_storage_key_non_vuoto |  |
| FOREIGN KEY | template_asset_asset_tipo_id_fkey | asset_tipo_id |
| FOREIGN KEY | template_asset_emittente_fiscale_id_fkey | emittente_fiscale_id |
| PRIMARY KEY | template_asset_pkey | id |
| UNIQUE | uq_template_asset_emittente_codice | emittente_fiscale_id, codice |
| UNIQUE | uq_template_asset_emittente_codice_interno | emittente_fiscale_id, codice_interno |
| UNIQUE | uq_template_asset_emittente_sha256 | emittente_fiscale_id, sha256 |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_template_asset_attivo | `CREATE INDEX ix_template_asset_attivo ON documenti.template_asset USING btree (attivo)` |
| ix_template_asset_storage_key | `CREATE INDEX ix_template_asset_storage_key ON documenti.template_asset USING btree (storage_key)` |
| ix_template_asset_tipo | `CREATE INDEX ix_template_asset_tipo ON documenti.template_asset USING btree (asset_tipo_id)` |
| template_asset_pkey | `CREATE UNIQUE INDEX template_asset_pkey ON documenti.template_asset USING btree (id)` |
| uq_template_asset_emittente_codice | `CREATE UNIQUE INDEX uq_template_asset_emittente_codice ON documenti.template_asset USING btree (emittente_fiscale_id, codice)` |
| uq_template_asset_emittente_codice_interno | `CREATE UNIQUE INDEX uq_template_asset_emittente_codice_interno ON documenti.template_asset USING btree (emittente_fiscale_id, codice_interno)` |
| uq_template_asset_emittente_sha256 | `CREATE UNIQUE INDEX uq_template_asset_emittente_sha256 ON documenti.template_asset USING btree (emittente_fiscale_id, sha256)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_asset_a10_block_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION documenti.trgfn_template_asset_block_delete()` |
| trg_template_asset_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_template_asset_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_template_asset_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_template_asset_a10_emittenti_fiscali_require_attivo_1ac740 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_template_asset_a10_emittenti_fiscali_require_attivo_1ac740 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_template_asset_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_template_asset_a10_protect_file_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_template_asset_protect_file()` |
| trg_template_asset_a10_tipi_asset_documento_require_atti_9bfc45 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_asset_documento', 'attivo', 'asset_tipo_id', 'id')` |
| trg_template_asset_a10_tipi_asset_documento_require_atti_9bfc45 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_asset_documento', 'attivo', 'asset_tipo_id', 'id')` |
| trg_template_asset_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_template_asset_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_template_asset_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_asset_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_asset_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_asset_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_asset_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_asset_id')` |
| trg_template_asset_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_asset_id')` |

---
{% include-markdown "signature-core.md" %}
