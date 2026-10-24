{% include-markdown "it/dbzero/documenti/manual/template_documenti.md" %}
# 📚 Tabella `template_documenti`

> 📝 **Descrizione**
>
> Contenitore logico dei template documentali per output, sorgente ed emittente.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_documento_output_id | bigint | NO |  |
| codice | character varying(120) | NO |  |
| codice_interno | character varying(120) | NO |  |
| descrizione | text | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| context_builder_code | character varying(160) | NO |  |
| file_name_pattern | text | YES |  |
| emittente_fiscale_id | bigint | YES |  |
| is_default | boolean | NO | false |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| standard | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_template_documenti_codice_interno_non_vuoto |  |
| CHECK | chk_template_documenti_codice_non_vuoto |  |
| CHECK | chk_template_documenti_context_builder_non_vuoto |  |
| CHECK | chk_template_documenti_descrizione_non_vuota |  |
| CHECK | chk_template_documenti_file_name_pattern_non_vuoto |  |
| CHECK | chk_template_documenti_standard_senza_emittente |  |
| FOREIGN KEY | template_documenti_emittente_fiscale_id_fkey | emittente_fiscale_id |
| FOREIGN KEY | template_documenti_sorgente_tipo_id_fkey | sorgente_tipo_id |
| FOREIGN KEY | template_documenti_tipo_documento_output_id_fkey | tipo_documento_output_id |
| PRIMARY KEY | template_documenti_pkey | id |
| UNIQUE | uq_template_documenti_emittente_sorgente_codice | emittente_fiscale_id, sorgente_tipo_id, codice |
| UNIQUE | uq_template_documenti_emittente_sorgente_codice_interno | emittente_fiscale_id, sorgente_tipo_id, codice_interno |
| UNIQUE | uq_template_documenti_id_tipo_sorgente | id, tipo_documento_output_id, sorgente_tipo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_template_documenti_tipo_sorgente_emittente | `CREATE INDEX ix_template_documenti_tipo_sorgente_emittente ON documenti.template_documenti USING btree (tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id)` |
| template_documenti_pkey | `CREATE UNIQUE INDEX template_documenti_pkey ON documenti.template_documenti USING btree (id)` |
| uq_template_documenti_default_attivo | `CREATE UNIQUE INDEX uq_template_documenti_default_attivo ON documenti.template_documenti USING btree (tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id) NULLS NOT DISTINCT WHERE ((is_default IS TRUE) AND (attivo IS TRUE))` |
| uq_template_documenti_emittente_sorgente_codice | `CREATE UNIQUE INDEX uq_template_documenti_emittente_sorgente_codice ON documenti.template_documenti USING btree (emittente_fiscale_id, sorgente_tipo_id, codice) NULLS NOT DISTINCT` |
| uq_template_documenti_emittente_sorgente_codice_interno | `CREATE UNIQUE INDEX uq_template_documenti_emittente_sorgente_codice_interno ON documenti.template_documenti USING btree (emittente_fiscale_id, sorgente_tipo_id, codice_interno) NULLS NOT DISTINCT` |
| uq_template_documenti_id_tipo_sorgente | `CREATE UNIQUE INDEX uq_template_documenti_id_tipo_sorgente ON documenti.template_documenti USING btree (id, tipo_documento_output_id, sorgente_tipo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_documenti_a05_guard_standard_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()` |
| trg_template_documenti_a05_guard_standard_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()` |
| trg_template_documenti_a05_guard_standard_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()` |
| trg_template_documenti_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_template_documenti_a10_documenti_generati_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'documenti_generati', 'template_documento_id', 'id', 'attivo')` |
| trg_template_documenti_a10_emittenti_fiscali_require_att_24b516 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_template_documenti_a10_emittenti_fiscali_require_att_24b516 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_template_documenti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE', 'standard', 'E_COLONNA_NON_MODIFICABILE')` |
| trg_template_documenti_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_template_documenti_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_template_documenti_a10_template_documenti_versioni_b_eea4ec | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'template_documenti_versioni', 'template_documento_id', 'id', 'attivo')` |
| trg_template_documenti_a10_tipi_documento_output_require_22dd12 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_documento_output', 'attivo', 'tipo_documento_output_id', 'id')` |
| trg_template_documenti_a10_tipi_documento_output_require_22dd12 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_documento_output', 'attivo', 'tipo_documento_output_id', 'id')` |
| trg_template_documenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_documenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_documenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_documenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_documenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_documenti_id')` |
| trg_template_documenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_documenti_id')` |

---
{% include-markdown "signature-core.md" %}
