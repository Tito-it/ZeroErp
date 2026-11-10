{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili_righe_stati.md" %}
# 📚 Tabella `vendite_contabili_righe_stati`

> 📝 **Descrizione**
>
> Lookup stati righe contabili vendite

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| codice | text | NO |  |
| codice_interno | text | NO |  |
| descrizione | text | NO |  |
| is_postabile | boolean | NO | false |
| is_final | boolean | NO | false |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| obsoleto_dal | date | YES |  |
| richiede_abbinamento | boolean | NO | false |
| lavorata | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_vendite_contabili_righe_stati | id |
| UNIQUE | uq_vendite_contabili_righe_stati_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_vendite_contabili_righe_stati | `CREATE UNIQUE INDEX pk_vendite_contabili_righe_stati ON pagamenti.vendite_contabili_righe_stati USING btree (id)` |
| uq_vendite_contabili_righe_stati_codice | `CREATE UNIQUE INDEX uq_vendite_contabili_righe_stati_codice ON pagamenti.vendite_contabili_righe_stati USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_contabili_righe_stati_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_vendite_contabili_righe_stati_a10_transizioni_stati_5a4234 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'transizioni_stati_contabile_riga', 'stato_da_id', 'id', 'attivo')` |
| trg_vendite_contabili_righe_stati_a10_transizioni_stati_988006 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'transizioni_stati_contabile_riga', 'stato_a_id', 'id', 'attivo')` |
| trg_vendite_contabili_righe_stati_a10_vendite_contabili_b3c071 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_contabili_righe', 'stato_id', 'id', 'attivo')` |
| trg_vendite_contabili_righe_stati_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vendite_contabili_righe_stati_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vendite_contabili_righe_stati_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_righe_stati_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
