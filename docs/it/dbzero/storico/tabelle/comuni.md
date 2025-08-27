{% include-markdown "it/dbzero/storico/manual/comuni.md" %}
# 📚 Tabella `comuni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.comuni_id_seq'::regclass) |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| comune_id | integer | YES |  |
| tx_id | uuid | YES |  |
| snapshot | jsonb | YES |  |
| tipo_operazione | smallint | YES |  |
| change_type | character | NO | 'A'::bpchar |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_comuni_comune_id | `CREATE INDEX ix_comuni_comune_id ON storico.comuni USING btree (comune_id)` |
| ix_storico_comuni_valid | `CREATE INDEX ix_storico_comuni_valid ON storico.comuni USING btree (valid_from, valid_to)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_comuni_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_comuni_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
