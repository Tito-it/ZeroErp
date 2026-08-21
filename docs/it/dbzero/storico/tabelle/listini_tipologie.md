{% include-markdown "it/dbzero/storico/manual/listini_tipologie.md" %}
# 📚 Tabella `listini_tipologie`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.listini_tipologie_id_seq'::regclass) |
| listini_tipologie_id | smallint | NO |  |
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
| PRIMARY KEY | pk_storico_listini_tipologie | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_listini_tipologie_listini_tipologie_id_fk | `CREATE INDEX ix_listini_tipologie_listini_tipologie_id_fk ON storico.listini_tipologie USING btree (listini_tipologie_id)` |
| pk_storico_listini_tipologie | `CREATE UNIQUE INDEX pk_storico_listini_tipologie ON storico.listini_tipologie USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_tipologie_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_tipologie_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
