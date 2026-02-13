{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili_righe.md" %}
# 📚 Tabella `vendite_contabili_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| contabile_id | bigint | NO |  |
| riferimento_ente | text | YES |  |
| data_pagamento | date | YES |  |
| data_valuta | date | YES |  |
| data_operazione | date | YES |  |
| importo | numeric | NO |  |
| fattura_id | bigint | YES |  |
| billing_account_id | bigint | YES |  |
| stato_id | smallint | NO |  |
| motivo_sospeso | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_vendite_contabili_righe_importo_non_zero |  |
| FOREIGN KEY | fk_vendite_contabili_righe_billing_account | billing_account_id |
| FOREIGN KEY | fk_vendite_contabili_righe_contabile | contabile_id |
| FOREIGN KEY | fk_vendite_contabili_righe_fattura | fattura_id |
| FOREIGN KEY | fk_vendite_contabili_righe_stato | stato_id |
| PRIMARY KEY | pk_vendite_contabili_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_vendite_contabili_righe | `CREATE UNIQUE INDEX pk_vendite_contabili_righe ON pagamenti.vendite_contabili_righe USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
