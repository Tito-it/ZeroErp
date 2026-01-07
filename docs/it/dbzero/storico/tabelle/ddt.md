# 📚 Tabella `ddt`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.ddt_id_seq'::regclass) |
| ddt_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_ddt | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ddt_ddt_id_fk | `CREATE INDEX ix_ddt_ddt_id_fk ON storico.ddt USING btree (ddt_id)` |
| pk_storico_ddt | `CREATE UNIQUE INDEX pk_storico_ddt ON storico.ddt USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
