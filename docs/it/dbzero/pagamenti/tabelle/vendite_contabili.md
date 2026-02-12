{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili.md" %}
# 📚 Tabella `vendite_contabili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| centro_riscossione_id | bigint | NO |  |
| data_contabile | date | NO |  |
| data_registrazione | date | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_vendite_contabili_centro_riscossione | centro_riscossione_id |
| PRIMARY KEY | pk_vendite_contabili | id |
| UNIQUE | uq_vendite_contabili_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_vendite_contabili | `CREATE UNIQUE INDEX pk_vendite_contabili ON pagamenti.vendite_contabili USING btree (id)` |
| uq_vendite_contabili_codice | `CREATE UNIQUE INDEX uq_vendite_contabili_codice ON pagamenti.vendite_contabili USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
