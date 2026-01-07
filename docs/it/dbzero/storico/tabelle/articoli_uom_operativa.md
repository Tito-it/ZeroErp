# 📚 Tabella `articoli_uom_operativa`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.articoli_uom_operativa_id_seq'::regclass) |
| articoli_uom_operativa_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_articoli_uom_operativa | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_uom_operativa_articoli_uom_operativa_id_fk | `CREATE INDEX ix_articoli_uom_operativa_articoli_uom_operativa_id_fk ON storico.articoli_uom_operativa USING btree (articoli_uom_operativa_id)` |
| pk_storico_articoli_uom_operativa | `CREATE UNIQUE INDEX pk_storico_articoli_uom_operativa ON storico.articoli_uom_operativa USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
