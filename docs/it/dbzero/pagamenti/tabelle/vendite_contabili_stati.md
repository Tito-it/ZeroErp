{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili_stati.md" %}
# 📚 Tabella `vendite_contabili_stati`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| codice | text | NO |  |
| codice_interno | text | NO |  |
| descrizione | text | NO |  |
| is_final | boolean | NO | false |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_lu_vendite_contabili_stati | id |
| UNIQUE | uq_vendite_contabili_stati_codice | codice |
| UNIQUE | uq_vendite_contabili_stati_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_lu_vendite_contabili_stati | `CREATE UNIQUE INDEX pk_lu_vendite_contabili_stati ON pagamenti.vendite_contabili_stati USING btree (id)` |
| uq_vendite_contabili_stati_codice | `CREATE UNIQUE INDEX uq_vendite_contabili_stati_codice ON pagamenti.vendite_contabili_stati USING btree (codice)` |
| uq_vendite_contabili_stati_codice_interno | `CREATE UNIQUE INDEX uq_vendite_contabili_stati_codice_interno ON pagamenti.vendite_contabili_stati USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
