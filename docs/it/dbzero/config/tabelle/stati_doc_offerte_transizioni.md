{% include-markdown "it/dbzero/config/manual/stati_doc_offerte_transizioni.md" %}
# 📚 Tabella `stati_doc_offerte_transizioni`

> 📝 **Descrizione**
>
> Matrice transizioni ammesse tra stati offerta commerciale. Consultata da vendite.trgfn_offerte_commerciali_guard_transizione. 5 transizioni (addendum A2): BOZZA-&gt;EMESSA|ANNULLATA, EMESSA-&gt;ACCETTATA|RIFIUTATA|SUPERATA. Nessuna transizione uscente da stati terminali. rev 2026-05-24.

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
| CHECK | ck_sdot_da_diverso_a |  |
| CHECK | ck_stati_doc_offerte_transizioni_meta_manuale_dichiarato |  |
| FOREIGN KEY | fk_sdot_a | stato_a_id |
| FOREIGN KEY | fk_sdot_da | stato_da_id |
| FOREIGN KEY | fk_stati_doc_offerte_transizioni_azioni_processo | azione_processo_codename |
| PRIMARY KEY | pk_stati_doc_offerte_transizioni | id |
| UNIQUE | uq_stati_doc_offerte_transizioni | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_doc_offerte_transizioni | `CREATE UNIQUE INDEX pk_stati_doc_offerte_transizioni ON config.stati_doc_offerte_transizioni USING btree (id)` |
| uq_stati_doc_offerte_transizioni | `CREATE UNIQUE INDEX uq_stati_doc_offerte_transizioni ON config.stati_doc_offerte_transizioni USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_offerte_transizioni_a10_stati_doc_offerte_54aa7f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_offerte', 'attivo', 'stato_da_id', 'id')` |
| trg_stati_doc_offerte_transizioni_a10_stati_doc_offerte_54aa7f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_offerte', 'attivo', 'stato_da_id', 'id')` |
| trg_stati_doc_offerte_transizioni_a10_stati_doc_offerte_9f88b6 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_offerte', 'attivo', 'stato_a_id', 'id')` |
| trg_stati_doc_offerte_transizioni_a10_stati_doc_offerte_9f88b6 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_offerte', 'attivo', 'stato_a_id', 'id')` |
| trg_stati_doc_offerte_transizioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_offerte_transizioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
