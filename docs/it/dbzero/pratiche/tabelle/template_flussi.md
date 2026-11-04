{% include-markdown "it/dbzero/pratiche/manual/template_flussi.md" %}
# 📚 Tabella `template_flussi`

> 📝 **Descrizione**
>
> Template step workflow per tipo prestazione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| tipo_prestazione_id | integer | NO |  |
| handler_id | integer | YES |  |
| codice | character varying(50) | NO |  |
| descrizione | text | NO |  |
| sequenza | integer | NO | 0 |
| obbligatorio | boolean | NO | false |
| direzione | character varying(10) | NO | 'INTERNA'::character varying |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| handler_params | jsonb | NO | '{}'::jsonb |
| ripetibilita | character varying(20) | NO | 'SE_NON_POSITIVO'::character varying |
| chiude_pratica | boolean | NO | false |
| azione_ui_id | integer | YES |  |
| modalita_esito | character varying(20) | NO | 'MANUALE'::character varying |
| esito_default | character varying(20) | YES |  |
| obsoleto_dal | date | YES |  |
| definizione_id | integer | NO |  |
| attende_sorgente_tipo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_template_flussi_chiusura_obbligatorio |  |
| CHECK | chk_template_flussi_direzione |  |
| CHECK | chk_template_flussi_modalita_esito |  |
| CHECK | chk_template_flussi_ripetibilita |  |
| FOREIGN KEY | fk_template_flussi_attende_sorgente | attende_sorgente_tipo_id |
| FOREIGN KEY | fk_template_flussi_azione_ui | azione_ui_id |
| FOREIGN KEY | fk_template_flussi_definizione | definizione_id, tipo_prestazione_id |
| FOREIGN KEY | fk_template_flussi_esito_default | esito_default |
| FOREIGN KEY | fk_template_flussi_handler | handler_id |
| FOREIGN KEY | fk_template_flussi_tipo_prestazione | tipo_prestazione_id |
| PRIMARY KEY | pk_pratiche_template_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_template_flussi | `CREATE UNIQUE INDEX pk_pratiche_template_flussi ON pratiche.template_flussi USING btree (id)` |
| uq_template_flussi_chiusura_definizione | `CREATE UNIQUE INDEX uq_template_flussi_chiusura_definizione ON pratiche.template_flussi USING btree (definizione_id) WHERE chiude_pratica` |
| uq_template_flussi_definizione_codice | `CREATE UNIQUE INDEX uq_template_flussi_definizione_codice ON pratiche.template_flussi USING btree (definizione_id, codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_flussi_a10_azioni_ui_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'azioni_ui', 'attivo', 'azione_ui_id', 'id')` |
| trg_template_flussi_a10_azioni_ui_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'azioni_ui', 'attivo', 'azione_ui_id', 'id')` |
| trg_template_flussi_a10_competenze_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'competenze_flussi', 'template_flusso_id', 'id', 'attivo')` |
| trg_template_flussi_a10_default_definizione_ins | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_default_definizione()` |
| trg_template_flussi_a10_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'flussi', 'template_flusso_id', 'id', 'attivo')` |
| trg_template_flussi_a10_formule_tempo_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'formule_tempo', 'template_flusso_a_id', 'id', 'attivo')` |
| trg_template_flussi_a10_guard_immutabile_iud | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_guard_immutabile()` |
| trg_template_flussi_a10_guard_immutabile_iud | BEFORE | DELETE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_guard_immutabile()` |
| trg_template_flussi_a10_guard_immutabile_iud | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_guard_immutabile()` |
| trg_template_flussi_a10_guard_modalita_esito_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_guard_modalita_esito()` |
| trg_template_flussi_a10_guard_modalita_esito_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_guard_modalita_esito()` |
| trg_template_flussi_a10_handler_flussi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'handler_flussi', 'attivo', 'handler_id', 'id')` |
| trg_template_flussi_a10_handler_flussi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'handler_flussi', 'attivo', 'handler_id', 'id')` |
| trg_template_flussi_a10_regole_generazione_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'regole_generazione', 'template_flusso_dest_id', 'id', 'attivo')` |
| trg_template_flussi_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'attende_sorgente_tipo_id', 'id')` |
| trg_template_flussi_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'attende_sorgente_tipo_id', 'id')` |
| trg_template_flussi_a10_template_flussi_avanzamento_proi_e10390 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_avanzamento_proiezione', 'template_flusso_id', 'id', 'attivo')` |
| trg_template_flussi_a10_template_flussi_canali_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_canali', 'template_flusso_id', 'id', 'attivo')` |
| trg_template_flussi_a10_template_flussi_handler_eventi_b_3bd6a7 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_handler_eventi', 'template_flusso_id', 'id', 'attivo')` |
| trg_template_flussi_a10_template_flussi_prerequisiti_blo_762b1c | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_prerequisiti', 'prerequisito_id', 'id', 'attivo')` |
| trg_template_flussi_a10_template_flussi_prerequisiti_blo_9af235 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi_prerequisiti', 'template_flusso_id', 'id', 'attivo')` |
| trg_template_flussi_a10_tipi_prestazione_require_attivo__70e854 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_template_flussi_a10_tipi_prestazione_require_attivo__70e854 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_template_flussi_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_template_flussi_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_template_flussi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_flussi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_flussi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_flussi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_flussi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_flussi_id')` |
| trg_template_flussi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_flussi_id')` |

---
{% include-markdown "signature-core.md" %}
