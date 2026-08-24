{% include-markdown "it/dbzero/storico/manual/fatture_righe.md" %}
# 📚 Tabella `fatture_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatture_righe_id_seq'::regclass) |
| fatture_righe_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatture_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_righe_fatture_righe_id_fk | `CREATE INDEX ix_fatture_righe_fatture_righe_id_fk ON storico.fatture_righe USING btree (fatture_righe_id)` |
| pk_storico_fatture_righe | `CREATE UNIQUE INDEX pk_storico_fatture_righe ON storico.fatture_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
