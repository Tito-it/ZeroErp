# 📚 Tabella `istanze_dati_precontrattuali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.istanze_dati_precontrattuali_id_seq'::regclass) |
| istanze_dati_precontrattuali_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_istanze_dati_precontrattuali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_istanze_dati_precontrattuali_istanze_dati_precontrattuali_id | `CREATE INDEX ix_istanze_dati_precontrattuali_istanze_dati_precontrattuali_id ON storico.istanze_dati_precontrattuali USING btree (istanze_dati_precontrattuali_id)` |
| pk_storico_istanze_dati_precontrattuali | `CREATE UNIQUE INDEX pk_storico_istanze_dati_precontrattuali ON storico.istanze_dati_precontrattuali USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_istanze_dati_precontrattuali_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_dati_precontrattuali_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
