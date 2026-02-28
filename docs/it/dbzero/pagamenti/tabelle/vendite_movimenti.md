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
| contabile_riga_id | bigint | YES |  |
| data_valuta | date | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_pagamenti_vendite_movimenti_ba | billing_account_id |
| FOREIGN KEY | fk_pagamenti_vendite_movimenti_fattura | fattura_id |
| FOREIGN KEY | fk_vendite_movimenti_centro_riscossione | centro_riscossione_id |
| FOREIGN KEY | fk_vendite_movimenti_contabile | contabile_id |
| FOREIGN KEY | fk_vendite_movimenti_contabile_riga | contabile_riga_id |
| PRIMARY KEY | pk_vendite_movimenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_vendite_movimenti | `CREATE UNIQUE INDEX pk_vendite_movimenti ON pagamenti.vendite_movimenti USING btree (id)` |
| uq_vendite_movimenti_contabile_riga | `CREATE UNIQUE INDEX uq_vendite_movimenti_contabile_riga ON pagamenti.vendite_movimenti USING btree (contabile_riga_id) WHERE (contabile_riga_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_movimenti_a10_centri_riscossione_require_att_4ac599 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id')` |
| trg_vendite_movimenti_a10_centri_riscossione_require_att_4ac599 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id')` |
| trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_guard_emittente_scope('fattura', 'fattura_id')` |
| trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_guard_emittente_scope('fattura', 'fattura_id')` |
| trg_vendite_movimenti_a10_sync_contabile_from_riga_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga()` |
| trg_vendite_movimenti_a10_sync_contabile_from_riga_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga()` |
| trg_vendite_movimenti_a10_vendite_contabili_righe_requir_913f22 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe', 'attivo', 'contabile_riga_id')` |
| trg_vendite_movimenti_a10_vendite_contabili_righe_requir_913f22 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe', 'attivo', 'contabile_riga_id')` |
| trg_vendite_movimenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_movimenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_movimenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vendite_movimenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
