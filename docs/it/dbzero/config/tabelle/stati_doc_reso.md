{% include-markdown "it/dbzero/config/manual/stati_doc_reso.md" %}
# 📚 Tabella `stati_doc_reso`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| fase | character varying | NO |  |
| is_abortito | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_reso_fase |  |
| PRIMARY KEY | pk_stati_doc_reso | id |
| UNIQUE | uq_stati_doc_reso_codice | codice |
| UNIQUE | uq_stati_doc_reso_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_reso_attivo | `CREATE INDEX ix_stati_doc_reso_attivo ON config.stati_doc_reso USING btree (attivo)` |
| ix_stati_doc_reso_ordine | `CREATE INDEX ix_stati_doc_reso_ordine ON config.stati_doc_reso USING btree (ordine)` |
| pk_stati_doc_reso | `CREATE UNIQUE INDEX pk_stati_doc_reso ON config.stati_doc_reso USING btree (id)` |
| uq_stati_doc_reso_codice | `CREATE UNIQUE INDEX uq_stati_doc_reso_codice ON config.stati_doc_reso USING btree (codice)` |
| uq_stati_doc_reso_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_reso_codice_interno ON config.stati_doc_reso USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_reso_a10_resi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi', 'stato_doc_reso_id', 'id', 'attivo')` |
| trg_stati_doc_reso_a10_transizioni_stati_reso_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_reso', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_doc_reso_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_reso_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
