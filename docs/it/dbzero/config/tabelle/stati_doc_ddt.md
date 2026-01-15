# 📚 Tabella `stati_doc_ddt`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_doc_ddt | id |
| UNIQUE | uq_stati_doc_ddt_codice | codice |
| UNIQUE | uq_stati_doc_ddt_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_ddt_attivo | `CREATE INDEX ix_stati_doc_ddt_attivo ON config.stati_doc_ddt USING btree (attivo)` |
| pk_stati_doc_ddt | `CREATE UNIQUE INDEX pk_stati_doc_ddt ON config.stati_doc_ddt USING btree (id)` |
| uq_stati_doc_ddt_codice | `CREATE UNIQUE INDEX uq_stati_doc_ddt_codice ON config.stati_doc_ddt USING btree (codice)` |
| uq_stati_doc_ddt_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_ddt_codice_interno ON config.stati_doc_ddt USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_ddt_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt', 'stato_doc_ddt_id', 'id')` |
| trg_stati_doc_ddt_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_ddt_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
