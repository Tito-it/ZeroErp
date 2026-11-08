{% include-markdown "it/dbzero/pratiche/manual/azioni_ui.md" %}
# 📚 Tabella `azioni_ui`

> 📝 **Descrizione**
>
> Catalogo attivita' UI lanciabili dal flusso pratica — chiavi per il registry FE.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| azione_ui_key | character varying(100) | NO |  |
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
| PRIMARY KEY | pk_pratiche_azioni_ui | id |
| UNIQUE | uq_pratiche_azioni_ui_codice | codice |
| UNIQUE | uq_pratiche_azioni_ui_key | azione_ui_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_azioni_ui | `CREATE UNIQUE INDEX pk_pratiche_azioni_ui ON pratiche.azioni_ui USING btree (id)` |
| uq_pratiche_azioni_ui_codice | `CREATE UNIQUE INDEX uq_pratiche_azioni_ui_codice ON pratiche.azioni_ui USING btree (codice)` |
| uq_pratiche_azioni_ui_key | `CREATE UNIQUE INDEX uq_pratiche_azioni_ui_key ON pratiche.azioni_ui USING btree (azione_ui_key)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_azioni_ui_a10_template_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi', 'azione_ui_id', 'id', 'attivo')` |
| trg_azioni_ui_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_azioni_ui_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_azioni_ui_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_azioni_ui_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
