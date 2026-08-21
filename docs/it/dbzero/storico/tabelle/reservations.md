{% include-markdown "it/dbzero/storico/manual/reservations.md" %}
# 📚 Tabella `reservations`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.reservations_id_seq'::regclass) |
| reservations_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_reservations | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_reservations_reservations_id_fk | `CREATE INDEX ix_reservations_reservations_id_fk ON storico.reservations USING btree (reservations_id)` |
| pk_storico_reservations | `CREATE UNIQUE INDEX pk_storico_reservations ON storico.reservations USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_reservations_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_reservations_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
