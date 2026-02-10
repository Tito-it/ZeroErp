# 📚 Tabella `fatturazione_lotti_attivita`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatturazione_lotti_attivita_id_seq'::regclass) |
| fatturazione_lotti_attivita_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatturazione_lotti_attivita | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatturazione_lotti_attivita_fatturazione_lotti_attivita_id_f | `CREATE INDEX ix_fatturazione_lotti_attivita_fatturazione_lotti_attivita_id_f ON storico.fatturazione_lotti_attivita USING btree (fatturazione_lotti_attivita_id)` |
| pk_storico_fatturazione_lotti_attivita | `CREATE UNIQUE INDEX pk_storico_fatturazione_lotti_attivita ON storico.fatturazione_lotti_attivita USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_attivita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_attivita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
