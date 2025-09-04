# 📚 Tabella `fatture`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatture_id_seq'::regclass) |
| fatture_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatture | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_fatture_id_fk | `CREATE INDEX ix_fatture_fatture_id_fk ON storico.fatture USING btree (fatture_id)` |
| pk_storico_fatture | `CREATE UNIQUE INDEX pk_storico_fatture ON storico.fatture USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
