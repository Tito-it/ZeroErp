{% include-markdown "it/dbzero/config/manual/stati_doc_preventivi.md" %}
# 📚 Tabella `stati_doc_preventivi`

> 📝 **Descrizione**
>
> Dominio stati del documento preventivo (codici stabili; descrizioni multilingua).

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
| fase | character varying(20) | NO |  |
| esito | character varying(50) | YES |  |
| terminale | boolean | NO | false |
| pdf_mode | character varying | NO |  |
| pdf_allow_allegati | boolean | NO |  |
| iniziale | boolean | NO | false |
| emissione | boolean | NO | false |
| accettazione | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_preventivi_abortito_attivo |  |
| CHECK | chk_stati_doc_preventivi_accettazione_attivo |  |
| CHECK | chk_stati_doc_preventivi_emissione_attivo |  |
| CHECK | chk_stati_doc_preventivi_fase |  |
| CHECK | chk_stati_doc_preventivi_iniziale_attivo |  |
| CHECK | chk_stati_doc_preventivi_pdf_mode |  |
| CHECK | chk_stati_doc_preventivi_terminale_chiuso |  |
| FOREIGN KEY | fk_stati_doc_preventivi_esito | esito |
| PRIMARY KEY | pk_stati_doc_preventivi | id |
| UNIQUE | uq_stati_doc_preventivi_codice | codice |
| UNIQUE | uq_stati_doc_preventivi_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_preventivi_attivo | `CREATE INDEX ix_stati_doc_preventivi_attivo ON config.stati_doc_preventivi USING btree (attivo)` |
| pk_stati_doc_preventivi | `CREATE UNIQUE INDEX pk_stati_doc_preventivi ON config.stati_doc_preventivi USING btree (id)` |
| uq_stati_doc_preventivi_abortito | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_abortito ON config.stati_doc_preventivi USING btree (is_abortito) WHERE is_abortito` |
| uq_stati_doc_preventivi_accettazione | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_accettazione ON config.stati_doc_preventivi USING btree (accettazione) WHERE accettazione` |
| uq_stati_doc_preventivi_codice | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_codice ON config.stati_doc_preventivi USING btree (codice)` |
| uq_stati_doc_preventivi_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_codice_interno ON config.stati_doc_preventivi USING btree (codice_interno)` |
| uq_stati_doc_preventivi_emissione | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_emissione ON config.stati_doc_preventivi USING btree (emissione) WHERE emissione` |
| uq_stati_doc_preventivi_iniziale | `CREATE UNIQUE INDEX uq_stati_doc_preventivi_iniziale ON config.stati_doc_preventivi USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_preventivi_a10_guard_esito_verdetto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_preventivi_a10_guard_esito_verdetto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_preventivi_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_preventivi_a10_preventivi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi', 'stato_doc_preventivo_id', 'id', 'attivo')` |
| trg_stati_doc_preventivi_a10_transizioni_stati_preventiv_24c434 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_preventivi', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_doc_preventivi_a10_transizioni_stati_preventiv_4353e6 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_preventivi', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_doc_preventivi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_preventivi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
