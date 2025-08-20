{% include-markdown "it/dbzero/storico/manual/stradario.md" %}
# 📚 Tabella `stradario`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.stradario_id_seq'::regclass) |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| stradario_id | integer | YES |  |
| snapshot | jsonb | YES |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_stradario_config | stradario_id, via_id_nuovo |
| PRIMARY KEY | pk_stradario | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_storico_stradario_stradario_id | `CREATE INDEX ix_storico_stradario_stradario_id ON storico.stradario USING btree (stradario_id)` |
| ix_storico_stradario_valid_periodo | `CREATE INDEX ix_storico_stradario_valid_periodo ON storico.stradario USING btree (valid_from, valid_to)` |
| pk_stradario | `CREATE UNIQUE INDEX pk_stradario ON storico.stradario USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stradario_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stradario_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
