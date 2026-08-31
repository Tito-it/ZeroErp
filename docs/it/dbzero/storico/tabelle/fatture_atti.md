# 📚 Tabella `fatture_atti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatture_atti_id_seq'::regclass) |
| fatture_atti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatture_atti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_atti_fatture_atti_id_fk | `CREATE INDEX ix_fatture_atti_fatture_atti_id_fk ON storico.fatture_atti USING btree (fatture_atti_id)` |
| pk_storico_fatture_atti | `CREATE UNIQUE INDEX pk_storico_fatture_atti ON storico.fatture_atti USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
