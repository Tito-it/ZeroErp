{% include-markdown "it/dbzero/config/manual/unita_organizzative.md" %}
# 📚 Tabella `unita_organizzative`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | text | NO |  |
| parent_id | integer | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_unita_organizzative_parent_not_self |  |
| FOREIGN KEY | fk_unita_organizzative_parent | parent_id |
| PRIMARY KEY | pk_unita_organizzative | id |
| UNIQUE | uq_unita_organizzative_codice | codice |
| UNIQUE | uq_unita_organizzative_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_unita_organizzative_parent_id | `CREATE INDEX ix_config_unita_organizzative_parent_id ON config.unita_organizzative USING btree (parent_id)` |
| pk_unita_organizzative | `CREATE UNIQUE INDEX pk_unita_organizzative ON config.unita_organizzative USING btree (id)` |
| uq_unita_organizzative_codice | `CREATE UNIQUE INDEX uq_unita_organizzative_codice ON config.unita_organizzative USING btree (codice)` |
| uq_unita_organizzative_codice_interno | `CREATE UNIQUE INDEX uq_unita_organizzative_codice_interno ON config.unita_organizzative USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_unita_organizzative_a10_competenze_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'competenze_flussi', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_contatti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'contatti', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_email_account_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_account', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_email_log_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_log', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_email_outbox_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_outbox', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_email_template_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_template', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'flussi', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_unita_organizzative_a10_pratiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'pratiche', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_profili_accesso_bindings_blo_9fc29b | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'profili_accesso_bindings', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_risorse_umane_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'risorse_umane', 'unita_organizzativa_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_unita_organizzative_block_de_619e29 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'unita_organizzative', 'parent_id', 'id', 'attivo')` |
| trg_unita_organizzative_a10_unita_organizzative_require__e47f05 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'parent_id', 'id')` |
| trg_unita_organizzative_a10_unita_organizzative_require__e47f05 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'parent_id', 'id')` |
| trg_unita_organizzative_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_unita_organizzative_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_unita_organizzative_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_unita_organizzative_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
