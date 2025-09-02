# 📚 Tabella `regole_fatturazione_articolo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.regole_fatturazione_articolo_id_seq'::regclass) |
| regole_fatturazione_articolo_id | integer | NO |  |
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
| PRIMARY KEY | pk_storico_regole_fatturazione_articolo | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_regole_fatturazione_articolo_regole_fatturazione_articolo_id | `CREATE INDEX ix_regole_fatturazione_articolo_regole_fatturazione_articolo_id ON storico.regole_fatturazione_articolo USING btree (regole_fatturazione_articolo_id)` |
| pk_storico_regole_fatturazione_articolo | `CREATE UNIQUE INDEX pk_storico_regole_fatturazione_articolo ON storico.regole_fatturazione_articolo USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_regole_fatturazione_articolo_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_regole_fatturazione_articolo_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
