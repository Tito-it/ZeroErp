# 📚 Tabella `ordini_righe_fulfillment`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.ordini_righe_fulfillment_id_seq'::regclass) |
| ordini_righe_fulfillment_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_ordini_righe_fulfillment | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_righe_fulfillment_ordini_righe_fulfillment_id_fk | `CREATE INDEX ix_ordini_righe_fulfillment_ordini_righe_fulfillment_id_fk ON storico.ordini_righe_fulfillment USING btree (ordini_righe_fulfillment_id)` |
| pk_storico_ordini_righe_fulfillment | `CREATE UNIQUE INDEX pk_storico_ordini_righe_fulfillment ON storico.ordini_righe_fulfillment USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_righe_fulfillment_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_fulfillment_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
