# 📚 Tabella `fatture_riepiloghi_iva`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| iva_id | integer | YES |  |
| natura_id | integer | YES |  |
| esigibilita | character | YES |  |
| split_payment | boolean | YES |  |
| imponibile | numeric | NO | 0 |
| imposta | numeric | NO | 0 |
| arrotondamento | numeric | NO | 0 |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_r_iva_esigibilita |  |
| FOREIGN KEY | fk_fatture_r_iva_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_r_iva_iva | iva_id |
| FOREIGN KEY | fk_fatture_r_iva_natura | natura_id |
| PRIMARY KEY | pk_fatture_r_iva | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_r_iva_fattura | `CREATE INDEX ix_fatture_r_iva_fattura ON vendite.fatture_riepiloghi_iva USING btree (fattura_id)` |
| pk_fatture_r_iva | `CREATE UNIQUE INDEX pk_fatture_r_iva ON vendite.fatture_riepiloghi_iva USING btree (id)` |
| uq_fatture_r_iva_key | `CREATE UNIQUE INDEX uq_fatture_r_iva_key ON vendite.fatture_riepiloghi_iva USING btree (fattura_id, COALESCE(natura_id, 0), COALESCE(esigibilita, 'I'::bpchar), COALESCE(split_payment, false), COALESCE(iva_id, 0))` |

---
{% include-markdown "signature-core.md" %}
