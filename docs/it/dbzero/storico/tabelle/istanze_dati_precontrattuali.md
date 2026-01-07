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

---
{% include-markdown "signature-core.md" %}
