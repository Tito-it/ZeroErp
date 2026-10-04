{% include-markdown "it/dbzero/storico/manual/utilities_tipi_ruolo.md" %}
# 📚 Tabella `utilities_tipi_ruolo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.utilities_tipi_ruolo_id_seq'::regclass) |
| utilities_tipi_ruolo_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_utilities_tipi_ruolo | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_utilities_tipi_ruolo_scope_ef | `CREATE INDEX ix_utilities_tipi_ruolo_scope_ef ON storico.utilities_tipi_ruolo USING btree (scope_emittente_fiscale_id)` |
| ix_utilities_tipi_ruolo_utilities_tipi_ruolo_id_fk | `CREATE INDEX ix_utilities_tipi_ruolo_utilities_tipi_ruolo_id_fk ON storico.utilities_tipi_ruolo USING btree (utilities_tipi_ruolo_id)` |
| pk_storico_utilities_tipi_ruolo | `CREATE UNIQUE INDEX pk_storico_utilities_tipi_ruolo ON storico.utilities_tipi_ruolo USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_utilities_tipi_ruolo_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_utilities_tipi_ruolo_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
