{% include-markdown "it/dbzero/anagrafiche/manual/catasto_unita_immobiliari_indirizzi.md" %}
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
| FOREIGN KEY | fk_cat_un_imm_indir_cat_un_imm | catasto_unita_id |
| FOREIGN KEY | fk_cat_un_imm_indir_indirizzo_dett | indirizzo_dettaglio_id |
| PRIMARY KEY | pk_catasto_unita_immobiliari_indirizzi | id |
| UNIQUE | uq_catunitaindir | catasto_unita_id, indirizzo_dettaglio_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_catasto_unita_immobiliari_indirizzi | `CREATE UNIQUE INDEX pk_catasto_unita_immobiliari_indirizzi ON anagrafiche.catasto_unita_immobiliari_indirizzi USING btree (id)` |
| uq_catunitaindir | `CREATE UNIQUE INDEX uq_catunitaindir ON anagrafiche.catasto_unita_immobiliari_indirizzi USING btree (catasto_unita_id, indirizzo_dettaglio_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_catasto_unita_immobiliari_indirizzi_a10_indirizzi_de_4328b2 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id')` |
| trg_catasto_unita_immobiliari_indirizzi_a10_indirizzi_de_4328b2 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id')` |

---
{% include-markdown "signature-core.md" %}
