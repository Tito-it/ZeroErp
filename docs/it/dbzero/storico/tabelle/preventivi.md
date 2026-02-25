# 📚 Tabella `preventivi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.preventivi_id_seq'::regclass) |
| preventivi_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_preventivi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_preventivi_preventivi_id_fk | `CREATE INDEX ix_preventivi_preventivi_id_fk ON storico.preventivi USING btree (preventivi_id)` |
| pk_storico_preventivi | `CREATE UNIQUE INDEX pk_storico_preventivi ON storico.preventivi USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
