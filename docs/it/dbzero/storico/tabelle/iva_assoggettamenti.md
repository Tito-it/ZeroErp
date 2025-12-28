# 📚 Tabella `iva_assoggettamenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.iva_assoggettamenti_id_seq'::regclass) |
| iva_assoggettamenti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_iva_assoggettamenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_iva_assoggettamenti_iva_assoggettamenti_id_fk | `CREATE INDEX ix_iva_assoggettamenti_iva_assoggettamenti_id_fk ON storico.iva_assoggettamenti USING btree (iva_assoggettamenti_id)` |
| pk_storico_iva_assoggettamenti | `CREATE UNIQUE INDEX pk_storico_iva_assoggettamenti ON storico.iva_assoggettamenti USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
