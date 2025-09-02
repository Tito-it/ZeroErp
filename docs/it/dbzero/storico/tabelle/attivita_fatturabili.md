# 📚 Tabella `attivita_fatturabili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.attivita_fatturabili_id_seq'::regclass) |
| attivita_fatturabili_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_attivita_fatturabili | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_attivita_fatturabili_attivita_fatturabili_id_fk | `CREATE INDEX ix_attivita_fatturabili_attivita_fatturabili_id_fk ON storico.attivita_fatturabili USING btree (attivita_fatturabili_id)` |
| pk_storico_attivita_fatturabili | `CREATE UNIQUE INDEX pk_storico_attivita_fatturabili ON storico.attivita_fatturabili USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_fatturabili_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
