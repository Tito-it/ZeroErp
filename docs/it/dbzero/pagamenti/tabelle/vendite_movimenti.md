{% include-markdown "it/dbzero/pagamenti/manual/vendite_movimenti.md" %}
# 📚 Tabella `vendite_movimenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| data_effettiva | date | NO |  |
| data_registrazione | date | NO |  |
| data_contabile | date | YES |  |
| importo | numeric | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| centro_riscossione_id | bigint | YES |  |
| data_per_calcolo_interessi | date | YES |  |
| escluso_da_interessi | boolean | NO | false |
| contabile_id | bigint | YES |  |
| data_contabilizzazione | date | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_pagamenti_vendite_movimenti_ba | billing_account_id |
| FOREIGN KEY | fk_pagamenti_vendite_movimenti_fattura | fattura_id |
| FOREIGN KEY | fk_vendite_movimenti_centro_riscossione | centro_riscossione_id |
| FOREIGN KEY | fk_vendite_movimenti_contabile | contabile_id |
| PRIMARY KEY | pk_vendite_movimenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_vendite_movimenti | `CREATE UNIQUE INDEX pk_vendite_movimenti ON pagamenti.vendite_movimenti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_movimenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
