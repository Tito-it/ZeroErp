# 📚 Tabella `fatture_rettifiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| rettificata_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_ret_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_ret_rettificata | rettificata_id |
| PRIMARY KEY | pk_fatture_rettifiche | id |
| UNIQUE | uq_fatture_rettifiche_pair | fattura_id, rettificata_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatret_rettificata | `CREATE INDEX ix_fatret_rettificata ON vendite.fatture_rettifiche USING btree (rettificata_id)` |
| ix_fatture_ret_fattura | `CREATE INDEX ix_fatture_ret_fattura ON vendite.fatture_rettifiche USING btree (fattura_id)` |
| pk_fatture_rettifiche | `CREATE UNIQUE INDEX pk_fatture_rettifiche ON vendite.fatture_rettifiche USING btree (id)` |
| uq_fatture_rettifiche_pair | `CREATE UNIQUE INDEX uq_fatture_rettifiche_pair ON vendite.fatture_rettifiche USING btree (fattura_id, rettificata_id)` |

---
{% include-markdown "signature-core.md" %}
