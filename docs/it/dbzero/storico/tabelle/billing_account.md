# 📚 Tabella `billing_account`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.billing_account_id_seq'::regclass) |
| billing_account_id | integer | NO |  |
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
| PRIMARY KEY | pk_storico_billing_account | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_billing_account_billing_account_id_fk | `CREATE INDEX ix_billing_account_billing_account_id_fk ON storico.billing_account USING btree (billing_account_id)` |
| pk_storico_billing_account | `CREATE UNIQUE INDEX pk_storico_billing_account ON storico.billing_account USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
