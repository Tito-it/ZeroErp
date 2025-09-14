# 📚 Tabella `ordini_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_id | bigint | NO |  |
| tipo_indirizzo_id | bigint | NO |  |
| snapshot | jsonb | NO | '{}'::jsonb |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ordini_indir_ordine | ordine_id |
| FOREIGN KEY | fk_ordini_indir_tipo | tipo_indirizzo_id |
| PRIMARY KEY | pk_ordini_indirizzi | id |
| UNIQUE | uq_ordini_indirizzi_uno_per_tipo | ordine_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_indir_ordine | `CREATE INDEX ix_ordini_indir_ordine ON vendite.ordini_indirizzi USING btree (ordine_id)` |
| pk_ordini_indirizzi | `CREATE UNIQUE INDEX pk_ordini_indirizzi ON vendite.ordini_indirizzi USING btree (id)` |
| uq_ordini_indirizzi_uno_per_tipo | `CREATE UNIQUE INDEX uq_ordini_indirizzi_uno_per_tipo ON vendite.ordini_indirizzi USING btree (ordine_id, tipo_indirizzo_id)` |

---
{% include-markdown "signature-core.md" %}
