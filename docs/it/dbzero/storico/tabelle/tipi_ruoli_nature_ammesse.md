{% include-markdown "it/dbzero/storico/manual/tipi_ruoli_nature_ammesse.md" %}
# 📚 Tabella `tipi_ruoli_nature_ammesse`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.tipi_ruoli_nature_ammesse_id_seq'::regclass) |
| tipi_ruoli_nature_ammesse_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_tipi_ruoli_nature_ammesse | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_ruoli_nature_ammesse_tipi_ruoli_nature_ammesse_id_fk | `CREATE INDEX ix_tipi_ruoli_nature_ammesse_tipi_ruoli_nature_ammesse_id_fk ON storico.tipi_ruoli_nature_ammesse USING btree (tipi_ruoli_nature_ammesse_id)` |
| pk_storico_tipi_ruoli_nature_ammesse | `CREATE UNIQUE INDEX pk_storico_tipi_ruoli_nature_ammesse ON storico.tipi_ruoli_nature_ammesse USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_ruoli_nature_ammesse_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_ruoli_nature_ammesse_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
