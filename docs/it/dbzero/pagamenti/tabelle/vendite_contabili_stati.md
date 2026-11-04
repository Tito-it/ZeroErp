{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili_stati.md" %}
# 📚 Tabella `vendite_contabili_stati`

> 📝 **Descrizione**
>
> Lookup stati contabili vendite

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
| obsoleto_dal | date | YES |  |
| is_registrabile | boolean | NO | false |
| righe_lavorabili | boolean | NO | false |

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

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_contabili_stati_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_vendite_contabili_stati_a10_transizioni_stati_contab_367732 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'transizioni_stati_contabile', 'stato_da_id', 'id', 'attivo')` |
| trg_vendite_contabili_stati_a10_transizioni_stati_contab_f067c7 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'transizioni_stati_contabile', 'stato_a_id', 'id', 'attivo')` |
| trg_vendite_contabili_stati_a10_vendite_contabili_block__662e3a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_contabili', 'stato_id', 'id', 'attivo')` |
| trg_vendite_contabili_stati_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vendite_contabili_stati_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vendite_contabili_stati_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_stati_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
