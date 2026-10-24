{% include-markdown "it/dbzero/config/manual/stati_doc_contratti.md" %}
# 📚 Tabella `stati_doc_contratti`

> 📝 **Descrizione**
>
> Dominio stati del documento contratto (codici stabili; descrizioni multilingua).

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
| is_abortito | boolean | NO | false |
| is_bozza | boolean | NO | false |
| fase | character varying(20) | NO |  |
| esito | character varying(50) | YES |  |
| terminale | boolean | NO | false |
| pdf_mode | character varying | NO |  |
| pdf_allow_allegati | boolean | NO |  |
| iniziale | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_contratti_fase |  |
| CHECK | chk_stati_doc_contratti_iniziale_attivo |  |
| CHECK | chk_stati_doc_contratti_pdf_mode |  |
| CHECK | chk_stati_doc_contratti_terminale_chiuso |  |
| FOREIGN KEY | fk_stati_doc_contratti_esito | esito |
| PRIMARY KEY | pk_stati_doc_contratti | id |
| UNIQUE | uq_stati_doc_contratti_codice | codice |
| UNIQUE | uq_stati_doc_contratti_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_contratti_attivo | `CREATE INDEX ix_stati_doc_contratti_attivo ON config.stati_doc_contratti USING btree (attivo)` |
| pk_stati_doc_contratti | `CREATE UNIQUE INDEX pk_stati_doc_contratti ON config.stati_doc_contratti USING btree (id)` |
| uq_stati_doc_contratti_codice | `CREATE UNIQUE INDEX uq_stati_doc_contratti_codice ON config.stati_doc_contratti USING btree (codice)` |
| uq_stati_doc_contratti_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_contratti_codice_interno ON config.stati_doc_contratti USING btree (codice_interno)` |
| uq_stati_doc_contratti_iniziale | `CREATE UNIQUE INDEX uq_stati_doc_contratti_iniziale ON config.stati_doc_contratti USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_contratti_a10_contratti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti', 'stato_doc_contratto_id', 'id', 'attivo')` |
| trg_stati_doc_contratti_a10_guard_esito_verdetto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_contratti_a10_guard_esito_verdetto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_contratti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_contratti_a10_transizioni_stati_contratti__70c7e0 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_contratti', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_doc_contratti_a10_transizioni_stati_contratti__98586e | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_contratti', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_doc_contratti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_contratti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
