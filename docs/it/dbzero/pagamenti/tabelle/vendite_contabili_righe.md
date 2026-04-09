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

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_contabili_righe_a10_vendite_contabili_righe__73024a | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_id', 'id')` |
| trg_vendite_contabili_righe_a10_vendite_contabili_righe__73024a | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_id', 'id')` |
| trg_vendite_contabili_righe_a10_vendite_movimenti_block__236436 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_movimenti', 'contabile_riga_id', 'id', 'attivo')` |
| trg_vendite_contabili_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vendite_contabili_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
