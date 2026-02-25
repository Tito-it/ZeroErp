# 📚 Tabella `commesse_attivita`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.commesse_attivita_id_seq'::regclass) |
| commesse_attivita_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_commesse_attivita | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_attivita_commesse_attivita_id_fk | `CREATE INDEX ix_commesse_attivita_commesse_attivita_id_fk ON storico.commesse_attivita USING btree (commesse_attivita_id)` |
| pk_storico_commesse_attivita | `CREATE UNIQUE INDEX pk_storico_commesse_attivita ON storico.commesse_attivita USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_attivita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_attivita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
