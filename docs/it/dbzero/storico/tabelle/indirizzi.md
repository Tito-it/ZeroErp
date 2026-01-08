{% include-markdown "it/dbzero/storico/manual/indirizzi.md" %}
# 📚 Tabella `indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| valid_from | timestamp with time zone | NO | CURRENT_DATE |
| valid_to | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | text | YES | CURRENT_USER |
| indirizzo_id | integer | YES |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | NO |  |
| tx_id | uuid | YES |  |
| change_type | character | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_indirizzi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_indirizzi | `CREATE UNIQUE INDEX pk_indirizzi ON storico.indirizzi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_indirizzi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
