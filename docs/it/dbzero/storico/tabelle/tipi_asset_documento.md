{% include-markdown "it/dbzero/storico/manual/tipi_asset_documento.md" %}
# 📚 Tabella `tipi_asset_documento`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.tipi_asset_documento_id_seq'::regclass) |
| tipi_asset_documento_id | bigint | NO |  |
| change_type | character(1) | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |
| origine_schema | text | NO |  |
| scope_emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_tipi_asset_documento | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_asset_documento_scope_ef | `CREATE INDEX ix_tipi_asset_documento_scope_ef ON storico.tipi_asset_documento USING btree (scope_emittente_fiscale_id)` |
| ix_tipi_asset_documento_tipi_asset_documento_id_fk | `CREATE INDEX ix_tipi_asset_documento_tipi_asset_documento_id_fk ON storico.tipi_asset_documento USING btree (tipi_asset_documento_id)` |
| pk_storico_tipi_asset_documento | `CREATE UNIQUE INDEX pk_storico_tipi_asset_documento ON storico.tipi_asset_documento USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_asset_documento_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_asset_documento_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
