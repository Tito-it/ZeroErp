{% include-markdown "it/dbzero/pratiche/manual/flussi.md" %}
# 📚 Tabella `flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| stato_id | integer | NO |  |
| flusso_padre_id | bigint | YES |  |
| risorsa_umana_id | bigint | YES |  |
| unita_organizzativa_id | integer | YES |  |
| sequenza | integer | NO | 0 |
| esito | character varying | YES |  |
| note_esito | text | YES |  |
| data_scadenza | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| data_fine | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_flussi_esito | esito |
| FOREIGN KEY | fk_flussi_flusso_padre | flusso_padre_id |
| FOREIGN KEY | fk_flussi_pratica | pratica_id |
| FOREIGN KEY | fk_flussi_risorsa_umana | risorsa_umana_id |
| FOREIGN KEY | fk_flussi_stato | stato_id |
| FOREIGN KEY | fk_flussi_template_flusso | template_flusso_id |
| FOREIGN KEY | fk_flussi_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | pk_pratiche_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_flussi | `CREATE UNIQUE INDEX pk_pratiche_flussi ON pratiche.flussi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_flussi_a10_guard_chiusura_prematura_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_chiusura_prematura()` |
| trg_flussi_a10_guard_esito_completato_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_esito_completato()` |
| trg_flussi_a10_guard_esito_completato_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_esito_completato()` |
| trg_flussi_a10_guard_pratica_terminale_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_pratica_terminale()` |
| trg_flussi_a10_guard_pratica_terminale_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_pratica_terminale()` |
| trg_flussi_a10_guard_prerequisiti_ins | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_prerequisiti()` |
| trg_flussi_a10_guard_ripetibilita_ins | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_ripetibilita()` |
| trg_flussi_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_guard_transizione()` |
| trg_flussi_a10_risorse_umane_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_flussi_a10_risorse_umane_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_flussi_a10_stati_flussi_pratiche_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_flussi_pratiche', 'attivo', 'stato_id', 'id')` |
| trg_flussi_a10_stati_flussi_pratiche_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_flussi_pratiche', 'attivo', 'stato_id', 'id')` |
| trg_flussi_a10_template_flussi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_flussi_a10_template_flussi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_flussi_a10_template_flussi_require_non_obsoleto_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('pratiche', 'template_flussi', 'obsoleto_dal', 'template_flusso_id', 'id')` |
| trg_flussi_a10_template_flussi_require_non_obsoleto_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('pratiche', 'template_flussi', 'obsoleto_dal', 'template_flusso_id', 'id')` |
| trg_flussi_a10_unita_organizzative_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_flussi_a10_unita_organizzative_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_flussi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_flussi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_flussi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_flussi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_flussi_z90_autochiusura_pratica_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_autochiusura_pratica()` |
| trg_flussi_z90_calcolo_tempo_completamento_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_calcolo_tempo_completamento()` |
| trg_flussi_z90_generazione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_generazione()` |
| trg_flussi_z90_giornale_assegnazione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_giornale_assegnazione()` |
| trg_flussi_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_flussi_giornale_ins()` |
| trg_flussi_z90_giornale_stato_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_flussi_giornale_stato()` |
| trg_flussi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('flussi_id')` |
| trg_flussi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('flussi_id')` |

---
{% include-markdown "signature-core.md" %}
