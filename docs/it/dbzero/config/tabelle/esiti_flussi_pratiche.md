{% include-markdown "it/dbzero/config/manual/esiti_flussi_pratiche.md" %}
# 📚 Tabella `esiti_flussi_pratiche`

> 📝 **Descrizione**
>
> Vocabolario data-driven degli esiti dei flussi (pratiche.flussi.esito). Referenziato via codice_interno da flussi.esito, template_flussi.esito_default e template_flussi_prerequisiti.esito_richiesto (FK, 20260701-02). Base strutturale di motore (POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE) seedata con lo schema; gli esiti di dominio (es. instradamento di un bivio) sono seedati dai domini in 80_data. Sostituisce l'enum cablato chk_flussi_esito.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| is_verdetto | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_esiti_flussi_pratiche | id |
| UNIQUE | uq_esiti_flussi_pratiche_codice | codice |
| UNIQUE | uq_esiti_flussi_pratiche_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_esiti_flussi_pratiche | `CREATE UNIQUE INDEX pk_esiti_flussi_pratiche ON config.esiti_flussi_pratiche USING btree (id)` |
| uq_esiti_flussi_pratiche_codice | `CREATE UNIQUE INDEX uq_esiti_flussi_pratiche_codice ON config.esiti_flussi_pratiche USING btree (codice)` |
| uq_esiti_flussi_pratiche_codice_interno | `CREATE UNIQUE INDEX uq_esiti_flussi_pratiche_codice_interno ON config.esiti_flussi_pratiche USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_esiti_flussi_pratiche_a10_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'flussi', 'esito', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_esiti_flussi_pratiche_a10_stati_doc_contratti_block_bac3f6 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_contratti', 'esito', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_stati_doc_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_ddt', 'esito', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_stati_doc_offerte_block_de_d7c20a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_offerte', 'esito', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_stati_doc_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_ordini', 'esito', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_stati_doc_preventivi_block_f297ae | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_preventivi', 'esito', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_stati_doc_reso_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_reso', 'esito', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_template_flussi_avanzament_76b1f7 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_avanzamento_proiezione', 'esito_richiesto', 'codice', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_template_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi', 'esito_default', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_template_flussi_handler_ev_bf23f3 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_handler_eventi', 'esito_richiesto', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a10_template_flussi_prerequisi_9e39f8 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_prerequisiti', 'esito_richiesto', 'codice_interno', 'attivo')` |
| trg_esiti_flussi_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_esiti_flussi_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_esiti_flussi_pratiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_esiti_flussi_pratiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
