# 📚 Tabella `articoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.articoli_id_seq'::regclass) |
| articoli_id | uuid | NO |  |
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
| FOREIGN KEY | fk_articoli | articoli_id |
| PRIMARY KEY | pk_storico_articoli | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_articoli_id_fk | `CREATE INDEX ix_articoli_articoli_id_fk ON storico.articoli USING btree (articoli_id)` |
| ix_storico_articoli_articolo_valid_from_desc | `CREATE INDEX ix_storico_articoli_articolo_valid_from_desc ON storico.articoli USING btree (articoli_id, valid_from DESC)` |
| pk_storico_articoli | `CREATE UNIQUE INDEX pk_storico_articoli ON storico.articoli USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
