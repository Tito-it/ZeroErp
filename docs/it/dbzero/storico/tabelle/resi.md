# 📚 Tabella `resi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.resi_id_seq'::regclass) |
| resi_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_resi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_resi_id_fk | `CREATE INDEX ix_resi_resi_id_fk ON storico.resi USING btree (resi_id)` |
| pk_storico_resi | `CREATE UNIQUE INDEX pk_storico_resi ON storico.resi USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
