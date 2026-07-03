{% include-markdown "it/dbzero/pratiche/manual/competenze_flussi.md" %}
# 📚 Tabella `competenze_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| unita_organizzativa_id | integer | NO |  |
| risorsa_umana_id | bigint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_competenze_flussi_risorse_umane | risorsa_umana_id |
| FOREIGN KEY | fk_competenze_flussi_template_flussi | template_flusso_id |
| FOREIGN KEY | fk_competenze_flussi_unita_organizzative | unita_organizzativa_id |
| PRIMARY KEY | pk_competenze_flussi | id |
| UNIQUE | uq_competenze_flussi | template_flusso_id, unita_organizzativa_id, risorsa_umana_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_competenze_flussi | `CREATE UNIQUE INDEX pk_competenze_flussi ON pratiche.competenze_flussi USING btree (id)` |
| uq_competenze_flussi | `CREATE UNIQUE INDEX uq_competenze_flussi ON pratiche.competenze_flussi USING btree (template_flusso_id, unita_organizzativa_id, risorsa_umana_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_competenze_flussi_a10_guard_immutabile_iud | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_competenze_flussi_a10_guard_immutabile_iud | BEFORE | DELETE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_competenze_flussi_a10_guard_immutabile_iud | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_competenze_flussi_a10_risorse_umane_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_competenze_flussi_a10_risorse_umane_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_competenze_flussi_a10_template_flussi_require_attivo_45bf7c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_competenze_flussi_a10_template_flussi_require_attivo_45bf7c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_competenze_flussi_a10_unita_organizzative_require_at_7c737d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_competenze_flussi_a10_unita_organizzative_require_at_7c737d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_competenze_flussi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_competenze_flussi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_competenze_flussi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_competenze_flussi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_competenze_flussi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('competenze_flussi_id')` |
| trg_competenze_flussi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('competenze_flussi_id')` |

---
{% include-markdown "signature-core.md" %}
