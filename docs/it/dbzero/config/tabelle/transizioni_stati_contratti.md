{% include-markdown "it/dbzero/config/manual/transizioni_stati_contratti.md" %}
# 📚 Tabella `transizioni_stati_contratti`

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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_tsc_da_diverso_a |  |
| FOREIGN KEY | fk_tsc_a | stato_a_id |
| FOREIGN KEY | fk_tsc_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_contratti | id |
| UNIQUE | uq_transizioni_stati_contratti | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_contratti | `CREATE UNIQUE INDEX pk_transizioni_stati_contratti ON config.transizioni_stati_contratti USING btree (id)` |
| uq_transizioni_stati_contratti | `CREATE UNIQUE INDEX uq_transizioni_stati_contratti ON config.transizioni_stati_contratti USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_contratti_a10_stati_doc_contratti__731a90 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_contratti_a10_stati_doc_contratti__731a90 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_contratti_a10_stati_doc_contratti__945a14 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_contratti_a10_stati_doc_contratti__945a14 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_contratti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_contratti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
