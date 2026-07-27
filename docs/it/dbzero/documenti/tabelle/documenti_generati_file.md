{% include-markdown "it/dbzero/documenti/manual/documenti_generati_file.md" %}
# 📚 Tabella `documenti_generati_file`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| documento_generato_id | bigint | NO |  |
| file_tipo_id | bigint | NO |  |
| mime_type | character varying | NO |  |
| file_name | text | NO |  |
| file_size_bytes | bigint | NO |  |
| storage_key | text | NO |  |
| sha256 | character varying | NO |  |
| ordinamento | integer | NO | 1 |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| is_principale | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_documenti_generati_file_file_name_non_vuoto |  |
| CHECK | chk_documenti_generati_file_mime_type_non_vuoto |  |
| CHECK | chk_documenti_generati_file_ordinamento_pos |  |
| CHECK | chk_documenti_generati_file_sha256_len |  |
| CHECK | chk_documenti_generati_file_size_pos |  |
| CHECK | chk_documenti_generati_file_storage_key_non_vuoto |  |
| FOREIGN KEY | documenti_generati_file_documento_generato_id_fkey | documento_generato_id |
| FOREIGN KEY | documenti_generati_file_file_tipo_id_fkey | file_tipo_id |
| PRIMARY KEY | documenti_generati_file_pkey | id |
| UNIQUE | uq_documenti_generati_file_doc_tipo_ord | documento_generato_id, file_tipo_id, ordinamento |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| documenti_generati_file_pkey | `CREATE UNIQUE INDEX documenti_generati_file_pkey ON documenti.documenti_generati_file USING btree (id)` |
| ix_documenti_generati_file_file_tipo | `CREATE INDEX ix_documenti_generati_file_file_tipo ON documenti.documenti_generati_file USING btree (file_tipo_id)` |
| ix_documenti_generati_file_storage_key | `CREATE INDEX ix_documenti_generati_file_storage_key ON documenti.documenti_generati_file USING btree (storage_key)` |
| uq_documenti_generati_file_doc_tipo_ord | `CREATE UNIQUE INDEX uq_documenti_generati_file_doc_tipo_ord ON documenti.documenti_generati_file USING btree (documento_generato_id, file_tipo_id, ordinamento)` |
| uq_documenti_generati_file_principale | `CREATE UNIQUE INDEX uq_documenti_generati_file_principale ON documenti.documenti_generati_file USING btree (documento_generato_id) WHERE (is_principale IS TRUE)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_documenti_generati_file_a10_protect_file_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_file_protect_file()` |
| trg_documenti_generati_file_a10_tipi_file_documento_requ_db402e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_file_documento', 'attivo', 'file_tipo_id', 'id')` |
| trg_documenti_generati_file_a10_tipi_file_documento_requ_db402e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'tipi_file_documento', 'attivo', 'file_tipo_id', 'id')` |
| trg_documenti_generati_file_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_file_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_file_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_documenti_generati_file_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
