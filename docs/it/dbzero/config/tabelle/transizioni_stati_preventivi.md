{% include-markdown "it/dbzero/config/manual/transizioni_stati_preventivi.md" %}
# 📚 Tabella `transizioni_stati_preventivi`

> 📝 **Descrizione**
>
> Transizioni ammesse tra stati preventivo vendita.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
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
| CHECK | ck_transizioni_stati_prev_da_diverso_a |  |
| CHECK | ck_transizioni_stati_prev_meta_ui |  |
| CHECK | ck_transizioni_stati_preventivi_meta_manuale_dichiarato |  |
| FOREIGN KEY | fk_transizioni_stati_prev_a | stato_a_id |
| FOREIGN KEY | fk_transizioni_stati_prev_da | stato_da_id |
| FOREIGN KEY | fk_transizioni_stati_preventivi_azioni_processo | azione_processo_codename |
| PRIMARY KEY | pk_transizioni_stati_preventivi | id |
| UNIQUE | uq_transizioni_stati_preventivi | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_preventivi | `CREATE UNIQUE INDEX pk_transizioni_stati_preventivi ON config.transizioni_stati_preventivi USING btree (id)` |
| uq_transizioni_stati_preventivi | `CREATE UNIQUE INDEX uq_transizioni_stati_preventivi ON config.transizioni_stati_preventivi USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_preventivi_a10_stati_doc_preventiv_2ff643 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_preventivi_a10_stati_doc_preventiv_2ff643 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_preventivi_a10_stati_doc_preventiv_62cee4 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_preventivi_a10_stati_doc_preventiv_62cee4 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_preventivi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_preventivi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
