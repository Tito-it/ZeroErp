# 📚 Tabella `clienti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| cliente_id | bigint | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_clienti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_storico_clienti | `CREATE UNIQUE INDEX pk_storico_clienti ON storico.clienti USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
