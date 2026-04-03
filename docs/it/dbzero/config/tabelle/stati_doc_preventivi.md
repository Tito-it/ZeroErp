{% include-markdown "it/dbzero/config/manual/stati_doc_preventivi.md" %}
# 📚 Tabella `stati_doc_preventivi`

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
| PRIMARY KEY | pk_stati_doc_preventivi | id |
| UNIQUE | uq_stati_doc_preventivi_codice | codice |
| UNIQUE | uq_stati_doc_preventivi_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_preventivi_attivo | `CREATE INDEX ix_stati_doc_preventivi_attivo ON config.stati_doc_preventivi USING btree (attivo)` |
| pk_stati_doc_preventivi | `CREATE UNIQUE INDEX pk_stati_doc_preventivi ON config.stati_doc_preventivi USING btree (id)` |
| uq_stati_doc_preventivi_codice | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_codice ON config.stati_doc_preventivi USING btree (codice)` |
| uq_stati_doc_preventivi_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_codice_interno ON config.stati_doc_preventivi USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_preventivi_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_preventivi_a10_preventivi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi', 'stato_doc_preventivo_id', 'id')` |
| trg_stati_doc_preventivi_a10_transizioni_stati_preventiv_24c434 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_preventivi', 'stato_da_id', 'id')` |
| trg_stati_doc_preventivi_a10_transizioni_stati_preventiv_4353e6 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_preventivi', 'stato_a_id', 'id')` |
| trg_stati_doc_preventivi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_preventivi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
