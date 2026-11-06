{% include-markdown "it/dbzero/documenti/manual/documenti_generati.md" %}
# 📚 Tabella `documenti_generati`

> 📝 **Descrizione**
>
> Registro storico delle generazioni persistite del motore documentale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| tipo_documento_output_id | bigint | NO |  |
| template_documento_id | bigint | NO |  |
| template_versione_id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | text | NO |  |
| sorgente_riga | bigint | YES |  |
| progressivo_sorgente | integer | NO |  |
| stato | character varying(30) | NO | 'GENERATO'::character varying |
| titolo | text | NO |  |
| nome_file | text | NO |  |
| context_json | jsonb | NO |  |
| context_hash | character varying(64) | NO |  |
| template_hash | character varying(64) | NO |  |
| pdf_hash | character varying(64) | NO |  |
| generato_da_user_id | integer | YES |  |
| generato_at | timestamp with time zone | NO | now() |
| emittente_fiscale_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_documenti_generati_context_hash_len |  |
| CHECK | chk_documenti_generati_context_json_obj |  |
| CHECK | chk_documenti_generati_nome_file_non_vuoto |  |
| CHECK | chk_documenti_generati_pdf_hash_len |  |
| CHECK | chk_documenti_generati_progressivo_pos |  |
| CHECK | chk_documenti_generati_sorgente_uid_non_vuoto |  |
| CHECK | chk_documenti_generati_stato |  |
| CHECK | chk_documenti_generati_template_hash_len |  |
| CHECK | chk_documenti_generati_titolo_non_vuoto |  |
| FOREIGN KEY | documenti_generati_emittente_fiscale_id_fkey | emittente_fiscale_id |
| FOREIGN KEY | documenti_generati_sorgente_tipo_id_fkey | sorgente_tipo_id |
| FOREIGN KEY | documenti_generati_template_documento_id_fkey | template_documento_id |
| FOREIGN KEY | documenti_generati_template_versione_id_fkey | template_versione_id |
| FOREIGN KEY | documenti_generati_tipo_documento_output_id_fkey | tipo_documento_output_id |
| FOREIGN KEY | fk_documenti_generati_django_auth_user | generato_da_user_id |
| PRIMARY KEY | documenti_generati_pkey | id |
| UNIQUE | uq_documenti_generati_sorgente_progressivo | sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente |
| UNIQUE | uq_documenti_generati_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| documenti_generati_pkey | `CREATE UNIQUE INDEX documenti_generati_pkey ON documenti.documenti_generati USING btree (id)` |
| ix_documenti_generati_generato_at | `CREATE INDEX ix_documenti_generati_generato_at ON documenti.documenti_generati USING btree (generato_at DESC)` |
| ix_documenti_generati_stato | `CREATE INDEX ix_documenti_generati_stato ON documenti.documenti_generati USING btree (stato)` |
| ix_documenti_generati_template_versione | `CREATE INDEX ix_documenti_generati_template_versione ON documenti.documenti_generati USING btree (template_versione_id)` |
| uq_documenti_generati_sorgente_progressivo | `CREATE UNIQUE INDEX uq_documenti_generati_sorgente_progressivo ON documenti.documenti_generati USING btree (sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente) NULLS NOT DISTINCT` |
| uq_documenti_generati_uid | `CREATE UNIQUE INDEX uq_documenti_generati_uid ON documenti.documenti_generati USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_documenti_generati_a10_block_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_block_delete()` |
| trg_documenti_generati_a10_check_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_check_coerenza()` |
| trg_documenti_generati_a10_check_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_check_coerenza()` |
| trg_documenti_generati_a10_emittenti_fiscali_require_att_e49311 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_documenti_generati_a10_emittenti_fiscali_require_att_e49311 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_documenti_generati_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_documenti_generati_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_documenti_generati_a10_guard_versione_contesto_ins | BEFORE | INSERT | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_guard_versione_contesto()` |
| trg_documenti_generati_a10_protect_snapshot_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_protect_snapshot()` |
| trg_documenti_generati_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_documenti_generati_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_documenti_generati_a10_template_documenti_require_at_e5973a | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti', 'attivo', 'template_documento_id', 'id')` |
| trg_documenti_generati_a10_template_documenti_require_at_e5973a | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti', 'attivo', 'template_documento_id', 'id')` |
| trg_documenti_generati_a10_template_documenti_versioni_r_2d8913 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti_versioni', 'attivo', 'template_versione_id', 'id')` |
| trg_documenti_generati_a10_template_documenti_versioni_r_2d8913 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti_versioni', 'attivo', 'template_versione_id', 'id')` |
| trg_documenti_generati_a10_tipi_documento_output_require_e76386 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_documento_output', 'attivo', 'tipo_documento_output_id', 'id')` |
| trg_documenti_generati_a10_tipi_documento_output_require_e76386 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_documento_output', 'attivo', 'tipo_documento_output_id', 'id')` |
| trg_documenti_generati_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_documenti_generati_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
