{% include-markdown "it/dbzero/pratiche/manual/template_flussi_prerequisiti.md" %}
# 📚 Tabella `template_flussi_prerequisiti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| prerequisito_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| esito_richiesto | character varying | YES |  |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_template_flussi_prereq_no_self |  |
| FOREIGN KEY | fk_template_flussi_prereq_flusso | template_flusso_id |
| FOREIGN KEY | fk_template_flussi_prereq_prerequisito | prerequisito_id |
| FOREIGN KEY | fk_tf_prereq_esito_richiesto | esito_richiesto |
| PRIMARY KEY | pk_pratiche_template_flussi_prerequisiti | id |
| UNIQUE | uq_pratiche_template_flussi_prereq_flusso_prereq | template_flusso_id, prerequisito_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_template_flussi_prerequisiti | `CREATE UNIQUE INDEX pk_pratiche_template_flussi_prerequisiti ON pratiche.template_flussi_prerequisiti USING btree (id)` |
| uq_pratiche_template_flussi_prereq_flusso_prereq | `CREATE UNIQUE INDEX uq_pratiche_template_flussi_prereq_flusso_prereq ON pratiche.template_flussi_prerequisiti USING btree (template_flusso_id, prerequisito_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_flussi_prerequisiti_a10_guard_immutabile_iud | BEFORE | DELETE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_template_flussi_prerequisiti_a10_guard_immutabile_iud | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_template_flussi_prerequisiti_a10_guard_immutabile_iud | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_template_flussi_prerequisiti_a10_template_flussi_req_838672 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_template_flussi_prerequisiti_a10_template_flussi_req_838672 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_template_flussi_prerequisiti_a10_template_flussi_req_ac3b2b | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'prerequisito_id', 'id')` |
| trg_template_flussi_prerequisiti_a10_template_flussi_req_ac3b2b | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'prerequisito_id', 'id')` |
| trg_template_flussi_prerequisiti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_flussi_prerequisiti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
