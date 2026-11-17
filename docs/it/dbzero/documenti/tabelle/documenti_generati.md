{% include-markdown "it/dbzero/documenti/manual/documenti_generati.md" %}
# 📚 Tabella `documenti_generati`

> 📝 **Descrizione**
>
> Il registro delle stampe emesse dal motore documentale: una riga per documento prodotto, con i dati congelati, le impronte di dati, template e PDF, il modello e la versione con cui e' nata e il documento da cui viene. E' storia: dopo la nascita cambia solo meta (documenti.trgfn_documenti_generati_protect_snapshot) e la riga non si cancella (E_DOCUMENTI_GENERATO_DELETE_BLOCKED). Alla nascita il modello va bene per il documento e stampa oggi con quella versione (documenti.trgfn_documenti_generati_check_coerenza), i dati hanno la forma che la versione legge (documenti.trgfn_documenti_generati_guard_versione_contesto), e a fine transazione la stampa ha il suo PDF principale (documenti.trgfn_documenti_generati_guard_file_principale). I file stanno in documenti.documenti_generati_file, la cronologia in documenti.documenti_generati_eventi. Un operatore vede e scrive le stampe delle aziende del suo perimetro.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| tipo_documento_output_id | bigint | NO |  |
| template_documento_id | bigint | NO |  |
| template_versione_id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | uuid | YES |  |
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
| CHECK | chk_documenti_generati_sorgente_forma |  |
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
| UNIQUE | uq_documenti_generati_sorgente_progressivo | sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, progressivo_sorgente |
| UNIQUE | uq_documenti_generati_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| documenti_generati_pkey | `CREATE UNIQUE INDEX documenti_generati_pkey ON documenti.documenti_generati USING btree (id)` |
| ix_documenti_generati_generato_at | `CREATE INDEX ix_documenti_generati_generato_at ON documenti.documenti_generati USING btree (generato_at DESC)` |
| ix_documenti_generati_sorgente_riga | `CREATE INDEX ix_documenti_generati_sorgente_riga ON documenti.documenti_generati USING btree (sorgente_tipo_id, sorgente_riga) WHERE (sorgente_riga IS NOT NULL)` |
| ix_documenti_generati_sorgente_uid | `CREATE INDEX ix_documenti_generati_sorgente_uid ON documenti.documenti_generati USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_uid IS NOT NULL)` |
| ix_documenti_generati_stato | `CREATE INDEX ix_documenti_generati_stato ON documenti.documenti_generati USING btree (stato)` |
| ix_documenti_generati_template_versione | `CREATE INDEX ix_documenti_generati_template_versione ON documenti.documenti_generati USING btree (template_versione_id)` |
| uq_documenti_generati_sorgente_progressivo | `CREATE UNIQUE INDEX uq_documenti_generati_sorgente_progressivo ON documenti.documenti_generati USING btree (sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, progressivo_sorgente) NULLS NOT DISTINCT` |
| uq_documenti_generati_uid | `CREATE UNIQUE INDEX uq_documenti_generati_uid ON documenti.documenti_generati USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_documenti_generati_a10_block_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_prevent_modification_generic('E_DOCUMENTI_GENERATO_DELETE_BLOCKED')` |
| trg_documenti_generati_a10_check_coerenza_ins | BEFORE | INSERT | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_check_coerenza()` |
| trg_documenti_generati_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_documenti_generati_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_documenti_generati_a10_guard_file_principale_ins | AFTER | INSERT | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_guard_file_principale()` |
| trg_documenti_generati_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_documenti_generati_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_documenti_generati_a10_guard_versione_contesto_ins | BEFORE | INSERT | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_guard_versione_contesto()` |
| trg_documenti_generati_a10_protect_snapshot_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_protect_snapshot()` |
| trg_documenti_generati_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_documenti_generati_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
