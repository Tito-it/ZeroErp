{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili_righe.md" %}
# 📚 Tabella `vendite_contabili_righe`

> 📝 **Descrizione**
>
> Righe contabili vendite importate/abbinate

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
| fondo_source_id | bigint | YES |  |
| scadenza_id | bigint | YES |  |
| forzata | boolean | NO | false |
| motivo_forzatura | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_vendite_contabili_righe_importo_finito |  |
| CHECK | chk_vendite_contabili_righe_importo_non_zero |  |
| FOREIGN KEY | fk_vendite_contabili_righe_billing_account | billing_account_id |
| FOREIGN KEY | fk_vendite_contabili_righe_contabile | contabile_id |
| FOREIGN KEY | fk_vendite_contabili_righe_fattura | fattura_id |
| FOREIGN KEY | fk_vendite_contabili_righe_fondo_source | fondo_source_id |
| FOREIGN KEY | fk_vendite_contabili_righe_scadenza | scadenza_id |
| FOREIGN KEY | fk_vendite_contabili_righe_stato | stato_id |
| PRIMARY KEY | pk_vendite_contabili_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_contabili_righe_contabile_id | `CREATE INDEX ix_vendite_contabili_righe_contabile_id ON pagamenti.vendite_contabili_righe USING btree (contabile_id)` |
| ix_vendite_contabili_righe_fattura_id | `CREATE INDEX ix_vendite_contabili_righe_fattura_id ON pagamenti.vendite_contabili_righe USING btree (fattura_id) WHERE (fattura_id IS NOT NULL)` |
| ix_vendite_contabili_righe_fondo_source_id | `CREATE INDEX ix_vendite_contabili_righe_fondo_source_id ON pagamenti.vendite_contabili_righe USING btree (fondo_source_id) WHERE (fondo_source_id IS NOT NULL)` |
| ix_vendite_contabili_righe_scadenza_id | `CREATE INDEX ix_vendite_contabili_righe_scadenza_id ON pagamenti.vendite_contabili_righe USING btree (scadenza_id) WHERE (scadenza_id IS NOT NULL)` |
| pk_vendite_contabili_righe | `CREATE UNIQUE INDEX pk_vendite_contabili_righe ON pagamenti.vendite_contabili_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_contabili_righe_a10_fatture_fondi_fattura_so_f71ffa | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'fatture_fondi_fattura_source', 'attivo', 'fondo_source_id', 'id')` |
| trg_vendite_contabili_righe_a10_fatture_fondi_fattura_so_f71ffa | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'fatture_fondi_fattura_source', 'attivo', 'fondo_source_id', 'id')` |
| trg_vendite_contabili_righe_a10_guard_contenuto_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_contenuto()` |
| trg_vendite_contabili_righe_a10_guard_contenuto_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_contenuto()` |
| trg_vendite_contabili_righe_a10_guard_contenuto_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_contenuto()` |
| trg_vendite_contabili_righe_a10_guard_distinta_finale_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale()` |
| trg_vendite_contabili_righe_a10_guard_distinta_finale_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale()` |
| trg_vendite_contabili_righe_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_id')` |
| trg_vendite_contabili_righe_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_id')` |
| trg_vendite_contabili_righe_a10_guard_rata_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_rata()` |
| trg_vendite_contabili_righe_a10_guard_rata_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_rata()` |
| trg_vendite_contabili_righe_a10_guard_scope_conto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('contabile', 'contabile_id')` |
| trg_vendite_contabili_righe_a10_guard_scope_conto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('contabile', 'contabile_id')` |
| trg_vendite_contabili_righe_a10_guard_stato_dati_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati()` |
| trg_vendite_contabili_righe_a10_guard_stato_dati_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati()` |
| trg_vendite_contabili_righe_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_transizione()` |
| trg_vendite_contabili_righe_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_vendite_contabili_righe_a10_vendite_contabili_righe__73024a | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_id', 'id')` |
| trg_vendite_contabili_righe_a10_vendite_contabili_righe__73024a | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_id', 'id')` |
| trg_vendite_contabili_righe_a10_vendite_movimenti_block__236436 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_movimenti', 'contabile_riga_id', 'id', 'attivo')` |
| trg_vendite_contabili_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vendite_contabili_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vendite_contabili_righe_z90_marca_fondo_eseguito_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito()` |
| trg_vendite_contabili_righe_z90_marca_fondo_eseguito_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito()` |

---
{% include-markdown "signature-core.md" %}
