{% include-markdown "it/dbzero/config/manual/stati_flussi_pratiche.md" %}
# 📚 Tabella `stati_flussi_pratiche`

> 📝 **Descrizione**
>
> Stati del ciclo di vita dei flussi operativi.

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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_flussi_pratiche | id |
| UNIQUE | uq_stati_flussi_pratiche_codice | codice |
| UNIQUE | uq_stati_flussi_pratiche_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_flussi_pratiche | `CREATE UNIQUE INDEX pk_stati_flussi_pratiche ON config.stati_flussi_pratiche USING btree (id)` |
| uq_stati_flussi_pratiche_codice | `CREATE UNIQUE INDEX uq_stati_flussi_pratiche_codice ON config.stati_flussi_pratiche USING btree (codice)` |
| uq_stati_flussi_pratiche_codice_interno | `CREATE UNIQUE INDEX uq_stati_flussi_pratiche_codice_interno ON config.stati_flussi_pratiche USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_flussi_pratiche_a10_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'flussi', 'stato_id', 'id', 'attivo')` |
| trg_stati_flussi_pratiche_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_flussi_pratiche_a10_transizioni_stati_flussi_p_4a3635 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_flussi_pratiche', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_flussi_pratiche_a10_transizioni_stati_flussi_p_5d4cb9 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_flussi_pratiche', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_flussi_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_flussi_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_flussi_pratiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_flussi_pratiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
