{% include-markdown "it/dbzero/documenti/manual/tipi_file_documento_formati.md" %}
# 📚 Tabella `tipi_file_documento_formati`

> 📝 **Descrizione**
>
> I formati di file che ogni tipo di file della stampa ammette: il PDF principale e gli allegati nascono solo in un formato abbinato al loro tipo (documenti.trgfn_guard_formato_ammesso). Il backend legge da qui la lista da controllare sui byte. Un abbinamento nasce o si ritira con un changeSet; l'applicazione legge soltanto.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| file_tipo_id | bigint | NO |  |
| formato_file_id | bigint | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_tipi_file_documento_formati_formato | formato_file_id |
| FOREIGN KEY | fk_tipi_file_documento_formati_tipo | file_tipo_id |
| PRIMARY KEY | pk_tipi_file_documento_formati | id |
| UNIQUE | uq_tipi_file_documento_formati | file_tipo_id, formato_file_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_file_documento_formati_formato_file_id | `CREATE INDEX ix_tipi_file_documento_formati_formato_file_id ON documenti.tipi_file_documento_formati USING btree (formato_file_id)` |
| pk_tipi_file_documento_formati | `CREATE UNIQUE INDEX pk_tipi_file_documento_formati ON documenti.tipi_file_documento_formati USING btree (id)` |
| uq_tipi_file_documento_formati | `CREATE UNIQUE INDEX uq_tipi_file_documento_formati ON documenti.tipi_file_documento_formati USING btree (file_tipo_id, formato_file_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_file_documento_formati_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_file_documento_formati_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_file_documento_formati_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_file_documento_formati_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
