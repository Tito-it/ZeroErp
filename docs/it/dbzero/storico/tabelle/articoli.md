# 📚 Tabella `articoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.articoli_id_seq'::regclass) |
| articoli_id | uuid | NO |  |
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
| PRIMARY KEY | pk_storico_articoli | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_articoli_id_fk | `CREATE INDEX ix_articoli_articoli_id_fk ON storico.articoli USING btree (articoli_id)` |
| pk_storico_articoli | `CREATE UNIQUE INDEX pk_storico_articoli ON storico.articoli USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
