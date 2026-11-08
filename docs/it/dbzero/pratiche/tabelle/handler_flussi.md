{% include-markdown "it/dbzero/pratiche/manual/handler_flussi.md" %}
# 📚 Tabella `handler_flussi`

> 📝 **Descrizione**
>
> Registry handler flusso — chiavi per mapping Django.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| handler_key | character varying(100) | NO |  |
| codice | character varying(50) | NO |  |
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
| PRIMARY KEY | pk_pratiche_handler_flussi | id |
| UNIQUE | uq_pratiche_handler_flussi_codice | codice |
| UNIQUE | uq_pratiche_handler_flussi_handler_key | handler_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_handler_flussi | `CREATE UNIQUE INDEX pk_pratiche_handler_flussi ON pratiche.handler_flussi USING btree (id)` |
| uq_pratiche_handler_flussi_codice | `CREATE UNIQUE INDEX uq_pratiche_handler_flussi_codice ON pratiche.handler_flussi USING btree (codice)` |
| uq_pratiche_handler_flussi_handler_key | `CREATE UNIQUE INDEX uq_pratiche_handler_flussi_handler_key ON pratiche.handler_flussi USING btree (handler_key)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_handler_flussi_a10_template_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi', 'handler_id', 'id', 'attivo')` |
| trg_handler_flussi_a10_template_flussi_handler_eventi_bl_109875 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_handler_eventi', 'handler_id', 'id', 'attivo')` |
| trg_handler_flussi_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_handler_flussi_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_handler_flussi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_handler_flussi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
