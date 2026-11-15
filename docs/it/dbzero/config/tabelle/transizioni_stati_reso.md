{% include-markdown "it/dbzero/config/manual/transizioni_stati_reso.md" %}
# 📚 Tabella `transizioni_stati_reso`

> 📝 **Descrizione**
>
> Matrice transizioni ammesse tra stati del reso di vendita (brief-db-resi-vendita §2.1). Fonte metadati UI per le azioni data-driven e grafo per vendite.trgfn_resi_guard_transizione. Mirror di config.transizioni_stati_ddt. Seed in 20260713-38. rev 2026-07-13.

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
| CHECK | ck_transizioni_stati_reso_da_diverso_a |  |
| CHECK | ck_transizioni_stati_reso_meta_manuale_dichiarato |  |
| CHECK | ck_transizioni_stati_reso_meta_ui |  |
| FOREIGN KEY | fk_transizioni_stati_reso_azioni_processo | azione_processo_codename |
| FOREIGN KEY | fk_tsr_a | stato_a_id |
| FOREIGN KEY | fk_tsr_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_reso | id |
| UNIQUE | uq_transizioni_stati_reso | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_reso | `CREATE UNIQUE INDEX pk_transizioni_stati_reso ON config.transizioni_stati_reso USING btree (id)` |
| uq_transizioni_stati_reso | `CREATE UNIQUE INDEX uq_transizioni_stati_reso ON config.transizioni_stati_reso USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_reso_a10_stati_doc_reso_require_at_28f28d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_reso', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_reso_a10_stati_doc_reso_require_at_28f28d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_reso', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_reso_a10_stati_doc_reso_require_at_de454c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_reso', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_reso_a10_stati_doc_reso_require_at_de454c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_reso', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_reso_a10_terminale_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale('vendite.resi')` |
| trg_transizioni_stati_reso_a10_terminale_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale('vendite.resi')` |
| trg_transizioni_stati_reso_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_reso_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
