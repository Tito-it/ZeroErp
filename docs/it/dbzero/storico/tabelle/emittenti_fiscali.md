# 📚 Tabella `emittenti_fiscali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.emittenti_fiscali_id_seq'::regclass) |
| emittenti_fiscali_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_emittenti_fiscali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_emittenti_fiscali_emittenti_fiscali_id_fk | `CREATE INDEX ix_emittenti_fiscali_emittenti_fiscali_id_fk ON storico.emittenti_fiscali USING btree (emittenti_fiscali_id)` |
| pk_storico_emittenti_fiscali | `CREATE UNIQUE INDEX pk_storico_emittenti_fiscali ON storico.emittenti_fiscali USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
