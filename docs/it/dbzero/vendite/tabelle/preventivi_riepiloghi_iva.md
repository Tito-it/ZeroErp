{% include-markdown "it/dbzero/vendite/manual/preventivi_riepiloghi_iva.md" %}
# 📚 Tabella `preventivi_riepiloghi_iva`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| preventivo_id | bigint | NO |  |
| iva_id | integer | YES |  |
| natura_id | integer | YES |  |
| esigibilita | character | YES |  |
| split_payment | boolean | YES |  |
| imponibile | numeric | NO | 0 |
| imposta | numeric | NO | 0 |
| arrotondamento | numeric | NO | 0 |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_preventivi_r_iva_iva | iva_id |
| FOREIGN KEY | fk_preventivi_r_iva_natura | natura_id |
| FOREIGN KEY | fk_preventivi_r_iva_preventivo | preventivo_id |
| PRIMARY KEY | pk_preventivi_r_iva | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_preventivi_r_iva_preventivo_id | `CREATE INDEX ix_vendite_preventivi_r_iva_preventivo_id ON vendite.preventivi_riepiloghi_iva USING btree (preventivo_id)` |
| pk_preventivi_r_iva | `CREATE UNIQUE INDEX pk_preventivi_r_iva ON vendite.preventivi_riepiloghi_iva USING btree (id)` |
| uq_preventivi_r_iva_key | `CREATE UNIQUE INDEX uq_preventivi_r_iva_key ON vendite.preventivi_riepiloghi_iva USING btree (preventivo_id, COALESCE(natura_id, 0), COALESCE(esigibilita, 'I'::bpchar), COALESCE(split_payment, false), COALESCE(iva_id, 0))` |

---
{% include-markdown "signature-core.md" %}
