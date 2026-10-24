{% include-markdown "it/dbzero/config/manual/stati_doc_offerte.md" %}
# 📚 Tabella `stati_doc_offerte`

> 📝 **Descrizione**
>
> Catalogo stati documento per vendite.offerte_commerciali. Cinque stati: BOZZA (editabile), EMESSA (proposta al cliente), ACCETTATA (terminale positivo), RIFIUTATA (terminale negativo), SUPERATA (terminale tecnico, set dal trigger trgfn_offerte_commerciali_revisione). codice_interno e' immutabile (lock via script.trgfn_lock_columns). Le transizioni ammesse sono configurate in config.stati_doc_offerte_transizioni (creata in Step 4). Pattern identico a config.stati_doc_contratti; senza is_abortito perche' le offerte non usano temporal-UNIQUE ne' is_abortito_snapshot. rev 2026-05-24.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(64) | NO |  |
| codice | character varying(64) | NO |  |
| descrizione | character varying(255) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| fase | character varying(20) | NO |  |
| esito | character varying(50) | YES |  |
| terminale | boolean | NO | false |
| pdf_mode | character varying | NO |  |
| pdf_allow_allegati | boolean | NO |  |
| is_abortito | boolean | NO | false |
| is_superato | boolean | NO | false |
| iniziale | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_offerte_fase |  |
| CHECK | chk_stati_doc_offerte_iniziale_attivo |  |
| CHECK | chk_stati_doc_offerte_pdf_mode |  |
| CHECK | chk_stati_doc_offerte_terminale_chiuso |  |
| FOREIGN KEY | fk_stati_doc_offerte_esito | esito |
| PRIMARY KEY | pk_stati_doc_offerte | id |
| UNIQUE | uq_stati_doc_offerte_codice | codice |
| UNIQUE | uq_stati_doc_offerte_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_offerte_attivo | `CREATE INDEX ix_stati_doc_offerte_attivo ON config.stati_doc_offerte USING btree (attivo)` |
| pk_stati_doc_offerte | `CREATE UNIQUE INDEX pk_stati_doc_offerte ON config.stati_doc_offerte USING btree (id)` |
| uq_stati_doc_offerte_codice | `CREATE UNIQUE INDEX uq_stati_doc_offerte_codice ON config.stati_doc_offerte USING btree (codice)` |
| uq_stati_doc_offerte_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_offerte_codice_interno ON config.stati_doc_offerte USING btree (codice_interno)` |
| uq_stati_doc_offerte_iniziale | `CREATE UNIQUE INDEX uq_stati_doc_offerte_iniziale ON config.stati_doc_offerte USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_offerte_a10_guard_esito_verdetto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_offerte_a10_guard_esito_verdetto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stati_doc_guard_esito_verdetto()` |
| trg_stati_doc_offerte_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_offerte_a10_offerte_commerciali_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali', 'stato_doc_offerta_id', 'id', 'attivo')` |
| trg_stati_doc_offerte_a10_stati_doc_offerte_transizioni__3acc96 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_offerte_transizioni', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_doc_offerte_a10_stati_doc_offerte_transizioni__89db14 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_offerte_transizioni', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_doc_offerte_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_offerte_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
