{% include-markdown "it/dbzero/pratiche/manual/tipi_prestazione.md" %}
# 📚 Tabella `tipi_prestazione`

> 📝 **Descrizione**
>
> Catalogo tipi di prestazione per le pratiche.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | text | NO |  |
| categoria | character varying(50) | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| pre_attivazione | boolean | NO | true |
| post_attivazione | boolean | NO | true |
| obsoleto_dal | date | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_pratiche_tipi_prestazione | id |
| UNIQUE | uq_pratiche_tipi_prestazione_codice | codice |
| UNIQUE | uq_pratiche_tipi_prestazione_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_tipi_prestazione | `CREATE UNIQUE INDEX pk_pratiche_tipi_prestazione ON pratiche.tipi_prestazione USING btree (id)` |
| uq_pratiche_tipi_prestazione_codice | `CREATE UNIQUE INDEX uq_pratiche_tipi_prestazione_codice ON pratiche.tipi_prestazione USING btree (codice)` |
| uq_pratiche_tipi_prestazione_codice_interno | `CREATE UNIQUE INDEX uq_pratiche_tipi_prestazione_codice_interno ON pratiche.tipi_prestazione USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_prestazione_a10_email_template_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_template', 'tipo_prestazione_id', 'id', 'attivo')` |
| trg_tipi_prestazione_a10_formule_tempo_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'formule_tempo', 'tipo_prestazione_id', 'id', 'attivo')` |
| trg_tipi_prestazione_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_prestazione_a10_pratiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'pratiche', 'tipo_prestazione_id', 'id', 'attivo')` |
| trg_tipi_prestazione_a10_regole_generazione_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'regole_generazione', 'tipo_prestazione_dest_id', 'id', 'attivo')` |
| trg_tipi_prestazione_a10_template_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi', 'tipo_prestazione_id', 'id', 'attivo')` |
| trg_tipi_prestazione_a10_workflow_definizioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'workflow_definizioni', 'tipo_prestazione_id', 'id', 'attivo')` |
| trg_tipi_prestazione_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_prestazione_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_prestazione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_prestazione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_prestazione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_prestazione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_prestazione_z90_bootstrap_definizione_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_tipi_prestazione_bootstrap_definizione()` |
| trg_tipi_prestazione_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('tipi_prestazione_id')` |
| trg_tipi_prestazione_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('tipi_prestazione_id')` |

---
{% include-markdown "signature-core.md" %}
