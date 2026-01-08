{% include-markdown "it/dbzero/storico/manual/dati_societari.md" %}
# 📚 Tabella `dati_societari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| dati_societari_id | bigint | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_dati_societari | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_storico_dati_societari | `CREATE UNIQUE INDEX pk_storico_dati_societari ON storico.dati_societari USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_dati_societari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_societari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_societari_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_societari_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
