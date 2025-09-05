# 📚 Tabella `fatture_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| tipo_indirizzo_id | bigint | NO |  |
| snapshot | jsonb | NO | '{}'::jsonb |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_indir_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_indir_tipo | tipo_indirizzo_id |
| PRIMARY KEY | pk_fatture_indirizzi | id |
| UNIQUE | uq_fatture_indirizzi_uno_per_tipo_ | fattura_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_indir_fattura | `CREATE INDEX ix_fatture_indir_fattura ON vendite.fatture_indirizzi USING btree (fattura_id)` |
| pk_fatture_indirizzi | `CREATE UNIQUE INDEX pk_fatture_indirizzi ON vendite.fatture_indirizzi USING btree (id)` |
| uq_fatture_indirizzi_uno_per_tipo_ | `CREATE UNIQUE INDEX uq_fatture_indirizzi_uno_per_tipo_ ON vendite.fatture_indirizzi USING btree (fattura_id, tipo_indirizzo_id)` |

---
{% include-markdown "signature-core.md" %}
