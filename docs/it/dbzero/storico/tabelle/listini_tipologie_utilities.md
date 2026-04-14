# 📚 Tabella `listini_tipologie_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.listini_tipologie_utilities_id_seq'::regclass) |
| listini_tipologie_utilities_id | integer | NO |  |
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
| PRIMARY KEY | pk_storico_listini_tipologie_utilities | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_listini_tipologie_utilities_listini_tipologie_utilities_id_f | `CREATE INDEX ix_listini_tipologie_utilities_listini_tipologie_utilities_id_f ON storico.listini_tipologie_utilities USING btree (listini_tipologie_utilities_id)` |
| pk_storico_listini_tipologie_utilities | `CREATE UNIQUE INDEX pk_storico_listini_tipologie_utilities ON storico.listini_tipologie_utilities USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_tipologie_utilities_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_tipologie_utilities_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
