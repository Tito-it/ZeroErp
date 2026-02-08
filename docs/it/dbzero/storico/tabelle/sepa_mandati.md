# 📚 Tabella `sepa_mandati`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.sepa_mandati_id_seq'::regclass) |
| sepa_mandati_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_sepa_mandati | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_sepa_mandati_sepa_mandati_id_fk | `CREATE INDEX ix_sepa_mandati_sepa_mandati_id_fk ON storico.sepa_mandati USING btree (sepa_mandati_id)` |
| pk_storico_sepa_mandati | `CREATE UNIQUE INDEX pk_storico_sepa_mandati ON storico.sepa_mandati USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sepa_mandati_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_sepa_mandati_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
