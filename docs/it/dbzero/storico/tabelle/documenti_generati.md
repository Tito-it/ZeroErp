# 📚 Tabella `documenti_generati`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.documenti_generati_id_seq'::regclass) |
| documenti_generati_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_documenti_generati | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_documenti_generati_documenti_generati_id_fk | `CREATE INDEX ix_documenti_generati_documenti_generati_id_fk ON storico.documenti_generati USING btree (documenti_generati_id)` |
| pk_storico_documenti_generati | `CREATE UNIQUE INDEX pk_storico_documenti_generati ON storico.documenti_generati USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
