{% include-markdown "it/dbzero/pagamenti/manual/transizioni_stati_contabile_riga.md" %}
# 📚 Tabella `transizioni_stati_contabile_riga`

> 📝 **Descrizione**
>
> Matrice delle transizioni ammesse fra stati della RIGA contabile (pagamenti.vendite_contabili_righe). Grafo letto da pagamenti.trgfn_vendite_contabili_righe_guard_transizione. Percorso di D14-a: DA_ABBINARE -&gt; ABBINATA|SOSPESA|SCARTATA, ABBINATA -&gt; POSTATA|DA_ABBINARE|SOSPESA, SOSPESA -&gt; ABBINATA|DA_ABBINARE|SCARTATA, SCARTATA -&gt; SOSPESA, POSTATA TERMINALE. ⚠️ SCARTATA non e' finale: da li' si torna a SOSPESA per riprenderla in mano. ⚠️ Le uscite da IMPORTATA non sono seminate finche' l'import da flusso non esiste.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_da_id | smallint | NO |  |
| stato_a_id | smallint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_transizioni_stati_contabile_riga_da_diverso_a |  |
| CHECK | ck_transizioni_stati_contabile_riga_meta_ui |  |
| FOREIGN KEY | fk_transizioni_stati_contabile_riga_a | stato_a_id |
| FOREIGN KEY | fk_transizioni_stati_contabile_riga_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_contabile_riga | id |
| UNIQUE | uq_transizioni_stati_contabile_riga | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_contabile_riga | `CREATE UNIQUE INDEX pk_transizioni_stati_contabile_riga ON pagamenti.transizioni_stati_contabile_riga USING btree (id)` |
| uq_transizioni_stati_contabile_riga | `CREATE UNIQUE INDEX uq_transizioni_stati_contabile_riga ON pagamenti.transizioni_stati_contabile_riga USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_contabile_riga_a10_vendite_contabi_232dd2 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_contabile_riga_a10_vendite_contabi_232dd2 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_contabile_riga_a10_vendite_contabi_26ab28 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_contabile_riga_a10_vendite_contabi_26ab28 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_righe_stati', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_contabile_riga_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_contabile_riga_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
