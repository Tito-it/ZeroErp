# 📚 Tabella `utilities_tipi_ruolo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.utilities_tipi_ruolo_id_seq'::regclass) |
| utilities_tipi_ruolo_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_utilities_tipi_ruolo | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_utilities_tipi_ruolo_utilities_tipi_ruolo_id_fk | `CREATE INDEX ix_utilities_tipi_ruolo_utilities_tipi_ruolo_id_fk ON storico.utilities_tipi_ruolo USING btree (utilities_tipi_ruolo_id)` |
| pk_storico_utilities_tipi_ruolo | `CREATE UNIQUE INDEX pk_storico_utilities_tipi_ruolo ON storico.utilities_tipi_ruolo USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
