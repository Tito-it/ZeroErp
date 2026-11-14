{% include-markdown "it/dbzero/config/manual/transizioni_stati_ddt.md" %}
# 📚 Tabella `transizioni_stati_ddt`

> 📝 **Descrizione**
>
> Matrice transizioni ammesse tra stati DDT di vendita (A-3). Fonte metadati UI per le azioni data-driven e grafo per vendite.trgfn_ddt_guard_transizione. Mirror di config.transizioni_stati_ordini. Seed matrice in 20260709-10. rev 2026-07-09.

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
| CHECK | ck_transizioni_stati_ddt_da_diverso_a |  |
| CHECK | ck_transizioni_stati_ddt_meta_manuale_dichiarato |  |
| CHECK | ck_transizioni_stati_ddt_meta_ui |  |
| FOREIGN KEY | fk_transizioni_stati_ddt_azioni_processo | azione_processo_codename |
| FOREIGN KEY | fk_tsd_a | stato_a_id |
| FOREIGN KEY | fk_tsd_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_ddt | id |
| UNIQUE | uq_transizioni_stati_ddt | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_ddt | `CREATE UNIQUE INDEX pk_transizioni_stati_ddt ON config.transizioni_stati_ddt USING btree (id)` |
| uq_transizioni_stati_ddt | `CREATE UNIQUE INDEX uq_transizioni_stati_ddt ON config.transizioni_stati_ddt USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_ddt_a10_stati_doc_ddt_require_atti_6babf9 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_ddt_a10_stati_doc_ddt_require_atti_6babf9 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_ddt_a10_stati_doc_ddt_require_atti_80e7d6 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_ddt_a10_stati_doc_ddt_require_atti_80e7d6 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_ddt_a10_terminale_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale('vendite.ddt')` |
| trg_transizioni_stati_ddt_a10_terminale_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale('vendite.ddt')` |
| trg_transizioni_stati_ddt_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_ddt_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
