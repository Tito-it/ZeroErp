{% include-markdown "it/dbzero/config/manual/stati_doc_ddt.md" %}
# 📚 Tabella `stati_doc_ddt`

> 📝 **Descrizione**
>
> Dominio stati del documento ddt (codici stabili; descrizioni multilingua).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(32) | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| pdf_mode | character varying | NO |  |
| pdf_allow_allegati | boolean | NO |  |
| fase | character varying(20) | NO |  |
| is_abortito | boolean | NO | false |
| iniziale | boolean | NO | false |
| emissione | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_ddt_emissione_attivo |  |
| CHECK | chk_stati_doc_ddt_fase |  |
| CHECK | chk_stati_doc_ddt_iniziale_attivo |  |
| CHECK | chk_stati_doc_ddt_pdf_mode |  |
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
| uq_stati_doc_ddt_emissione | `CREATE UNIQUE INDEX uq_stati_doc_ddt_emissione ON config.stati_doc_ddt USING btree (emissione) WHERE emissione` |
| uq_stati_doc_ddt_iniziale | `CREATE UNIQUE INDEX uq_stati_doc_ddt_iniziale ON config.stati_doc_ddt USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_ddt_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt', 'stato_doc_ddt_id', 'id', 'attivo')` |
| trg_stati_doc_ddt_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_ddt_a10_transizioni_stati_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_ddt', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_doc_ddt_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_ddt_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
