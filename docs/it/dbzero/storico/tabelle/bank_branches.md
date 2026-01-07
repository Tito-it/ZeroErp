# 📚 Tabella `bank_branches`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.bank_branches_id_seq'::regclass) |
| bank_branches_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_bank_branches | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_bank_branches_bank_branches_id_fk | `CREATE INDEX ix_bank_branches_bank_branches_id_fk ON storico.bank_branches USING btree (bank_branches_id)` |
| pk_storico_bank_branches | `CREATE UNIQUE INDEX pk_storico_bank_branches ON storico.bank_branches USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
