{% include-markdown "it/dbzero/config/manual/formati_file.md" %}
# 📚 Tabella `formati_file`

> 📝 **Descrizione**
>
> I formati di file che il sistema riconosce: un tipo MIME con la sua estensione. I tipi che accettano un file abbinano qui i formati che ammettono (documenti.tipi_asset_documento_formati, documenti.tipi_file_documento_formati). Un formato nasce con un changeSet; l'applicazione li legge soltanto.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| codice | character varying(40) | NO |  |
| descrizione | character varying(255) | NO |  |
| etichetta_key | character varying(120) | NO |  |
| ordine | smallint | YES |  |
| mime_type | character varying(255) | NO |  |
| estensione | character varying(16) | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_formati_file_codice_interno_non_vuoto |  |
| CHECK | chk_formati_file_codice_non_vuoto |  |
| CHECK | chk_formati_file_descrizione_non_vuota |  |
| CHECK | chk_formati_file_estensione_forma |  |
| CHECK | chk_formati_file_mime_type_forma |  |
| PRIMARY KEY | pk_formati_file | id |
| UNIQUE | uq_formati_file_codice | codice |
| UNIQUE | uq_formati_file_codice_interno | codice_interno |
| UNIQUE | uq_formati_file_mime_type | mime_type |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_formati_file | `CREATE UNIQUE INDEX pk_formati_file ON config.formati_file USING btree (id)` |
| uq_formati_file_codice | `CREATE UNIQUE INDEX uq_formati_file_codice ON config.formati_file USING btree (codice)` |
| uq_formati_file_codice_interno | `CREATE UNIQUE INDEX uq_formati_file_codice_interno ON config.formati_file USING btree (codice_interno)` |
| uq_formati_file_mime_type | `CREATE UNIQUE INDEX uq_formati_file_mime_type ON config.formati_file USING btree (mime_type)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_formati_file_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_formati_file_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_formati_file_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_formati_file_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_formati_file_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_formati_file_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_formati_file_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
