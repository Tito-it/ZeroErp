{% include-markdown "it/dbzero/config/manual/transizioni_stati_ordini.md" %}
# 📚 Tabella `transizioni_stati_ordini`

> 📝 **Descrizione**
>
> Matrice transizioni ammesse tra stati ordine di vendita. Fonte metadati UI per script.fn_available_actions_ordine e grafo per vendite.trgfn_ordini_guard_transizione. Manuali attive: DRAFT-&gt;CONFERMATO, DRAFT-&gt;ANNULLATO. CONFERMATO-&gt;ANNULLATO presente ma attivo=false (riabilitabile). Stati a valle (ALLOCATO/SPEDITO/CONSEGNATO/FATTURATO) fuori matrice. rev 2026-06-05.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_da_id | bigint | NO |  |
| stato_a_id | bigint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| azione_processo_codename | character varying(100) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_transizioni_stati_ord_da_diverso_a |  |
| CHECK | ck_transizioni_stati_ord_meta_ui |  |
| FOREIGN KEY | fk_transizioni_stati_ordini_azioni_processo | azione_processo_codename |
| FOREIGN KEY | fk_tso_a | stato_a_id |
| FOREIGN KEY | fk_tso_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_ordini | id |
| UNIQUE | uq_transizioni_stati_ordini | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_ordini | `CREATE UNIQUE INDEX pk_transizioni_stati_ordini ON config.transizioni_stati_ordini USING btree (id)` |
| uq_transizioni_stati_ordini | `CREATE UNIQUE INDEX uq_transizioni_stati_ordini ON config.transizioni_stati_ordini USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_ordini_a10_stati_doc_ordini_requir_705aa8 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_ordini_a10_stati_doc_ordini_requir_705aa8 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_ordini_a10_stati_doc_ordini_requir_ee5148 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_ordini_a10_stati_doc_ordini_requir_ee5148 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_ordini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_ordini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
