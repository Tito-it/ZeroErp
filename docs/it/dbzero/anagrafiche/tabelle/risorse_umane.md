{% include-markdown "it/dbzero/anagrafiche/manual/risorse_umane.md" %}
# 📚 Tabella `risorse_umane`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| qualifica_id | integer | NO |  |
| unita_organizzativa_id | integer | YES |  |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| soggetto_id | uuid | NO |  |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_risorse_umane_date |  |
| FOREIGN KEY | fk_risorse_umane_qualifiche | qualifica_id |
| FOREIGN KEY | fk_risorse_umane_soggetti | soggetto_id |
| FOREIGN KEY | fk_risorse_umane_soggetti_ruoli | soggetto_ruolo_id |
| FOREIGN KEY | fk_risorse_umane_unita_organizzative | unita_organizzativa_id |
| PRIMARY KEY | pk_risorse_umane | id |
| UNIQUE | uq_risorse_umane_soggetto_ruolo | soggetto_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_risorse_umane_qualifica_id | `CREATE INDEX ix_anagrafiche_risorse_umane_qualifica_id ON anagrafiche.risorse_umane USING btree (qualifica_id)` |
| ix_anagrafiche_risorse_umane_soggetto_id | `CREATE INDEX ix_anagrafiche_risorse_umane_soggetto_id ON anagrafiche.risorse_umane USING btree (soggetto_id)` |
| ix_anagrafiche_risorse_umane_unita_organizzativa_id | `CREATE INDEX ix_anagrafiche_risorse_umane_unita_organizzativa_id ON anagrafiche.risorse_umane USING btree (unita_organizzativa_id)` |
| pk_risorse_umane | `CREATE UNIQUE INDEX pk_risorse_umane ON anagrafiche.risorse_umane USING btree (id)` |
| uq_risorse_umane_soggetto_ruolo | `CREATE UNIQUE INDEX uq_risorse_umane_soggetto_ruolo ON anagrafiche.risorse_umane USING btree (soggetto_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_risorse_umane_a10_commesse_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse', 'responsabile_risorsa_umana_id', 'id', 'attivo')` |
| trg_risorse_umane_a10_competenze_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'competenze_flussi', 'risorsa_umana_id', 'id', 'attivo')` |
| trg_risorse_umane_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_risorse_umane_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_risorse_umane_a10_delete_block_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_risorse_umane_a10_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'flussi', 'risorsa_umana_id', 'id', 'attivo')` |
| trg_risorse_umane_a10_guard_identita_attiva_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_guard_identita_attiva()` |
| trg_risorse_umane_a10_guard_ruolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_guard_ruolo()` |
| trg_risorse_umane_a10_guard_ruolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_guard_ruolo()` |
| trg_risorse_umane_a10_guard_ultimo_super_admin_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin()` |
| trg_risorse_umane_a10_pratiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'pratiche', 'risorsa_umana_id', 'id', 'attivo')` |
| trg_risorse_umane_a10_qualifiche_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'qualifiche', 'attivo', 'qualifica_id', 'id')` |
| trg_risorse_umane_a10_qualifiche_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'qualifiche', 'attivo', 'qualifica_id', 'id')` |
| trg_risorse_umane_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_risorse_umane_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_risorse_umane_a10_unita_organizzative_require_attivo_c6ba90 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_risorse_umane_a10_unita_organizzative_require_attivo_c6ba90 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_risorse_umane_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_risorse_umane_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_risorse_umane_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_risorse_umane_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_risorse_umane_z90_notify_cambio_reparto_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_notify_cambio_reparto()` |
| trg_risorse_umane_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('risorse_umane_id')` |
| trg_risorse_umane_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('risorse_umane_id')` |
| trg_risorse_umane_z90_sync_auth_user_active_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()` |

---
{% include-markdown "signature-core.md" %}
