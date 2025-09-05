# 📚 Tabella `resellers`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.resellers_id_seq'::regclass) |
| resellers_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_resellers | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resellers_resellers_id_fk | `CREATE INDEX ix_resellers_resellers_id_fk ON storico.resellers USING btree (resellers_id)` |
| pk_storico_resellers | `CREATE UNIQUE INDEX pk_storico_resellers ON storico.resellers USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
