# 📚 Tabella `catasto_unita_immobiliari_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| catasto_unita_id | bigint | NO |  |
| indirizzo_dettaglio_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_catunitaindir_indirizzo | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_catunitaindir_unita | catasto_unita_id |
| PRIMARY KEY | pk_catasto_unita_immobiliari_indirizzi | id |
| UNIQUE | uq_catunitaindir | catasto_unita_id, indirizzo_dettaglio_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_catasto_unita_immobiliari_indirizzi | `CREATE UNIQUE INDEX pk_catasto_unita_immobiliari_indirizzi ON anagrafiche.catasto_unita_immobiliari_indirizzi USING btree (id)` |
| uq_catunitaindir | `CREATE UNIQUE INDEX uq_catunitaindir ON anagrafiche.catasto_unita_immobiliari_indirizzi USING btree (catasto_unita_id, indirizzo_dettaglio_id)` |

---
{% include-markdown "signature-core.md" %}
