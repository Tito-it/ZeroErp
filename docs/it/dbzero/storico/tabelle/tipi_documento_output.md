{% include-markdown "it/dbzero/storico/manual/tipi_documento_output.md" %}
# 📚 Tabella `tipi_documento_output`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.tipi_documento_output_id_seq'::regclass) |
| tipi_documento_output_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_tipi_documento_output | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_documento_output_tipi_documento_output_id_fk | `CREATE INDEX ix_tipi_documento_output_tipi_documento_output_id_fk ON storico.tipi_documento_output USING btree (tipi_documento_output_id)` |
| pk_storico_tipi_documento_output | `CREATE UNIQUE INDEX pk_storico_tipi_documento_output ON storico.tipi_documento_output USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_documento_output_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_documento_output_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
