{% include-markdown "it/dbzero/documenti/manual/tipi_file_documento.md" %}
# 📚 Tabella `tipi_file_documento`

> 📝 **Descrizione**
>
> Lookup dei tipi file persistiti per un documento generato.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(80) | NO |  |
| codice_interno | character varying(80) | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_file_documento_codice_interno_non_vuoto |  |
| CHECK | chk_tipi_file_documento_codice_non_vuoto |  |
| CHECK | chk_tipi_file_documento_descrizione_non_vuota |  |
| PRIMARY KEY | tipi_file_documento_pkey | id |
| UNIQUE | uq_tipi_file_documento_codice | codice |
| UNIQUE | uq_tipi_file_documento_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| tipi_file_documento_pkey | `CREATE UNIQUE INDEX tipi_file_documento_pkey ON documenti.tipi_file_documento USING btree (id)` |
| uq_tipi_file_documento_codice | `CREATE UNIQUE INDEX uq_tipi_file_documento_codice ON documenti.tipi_file_documento USING btree (codice)` |
| uq_tipi_file_documento_codice_interno | `CREATE UNIQUE INDEX uq_tipi_file_documento_codice_interno ON documenti.tipi_file_documento USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_file_documento_a10_documenti_generati_file_bloc_670ad3 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'documenti_generati_file', 'file_tipo_id', 'id', 'attivo')` |
| trg_tipi_file_documento_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_file_documento_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_file_documento_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_file_documento_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_file_documento_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_file_documento_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_file_documento_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_file_documento_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('tipi_file_documento_id')` |
| trg_tipi_file_documento_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('tipi_file_documento_id')` |

---
{% include-markdown "signature-core.md" %}
