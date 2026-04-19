# 📚 Tabella `_legacy_risorse_umane_auth_user`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| risorsa_umana_id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| ruolo_sistema | USER-DEFINED | NO | 'OPERATIVO'::config.ruolo_sistema |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| tentativi_falliti | smallint | NO | 0 |
| bloccato_fino_a | timestamp with time zone | YES |  |
| deve_cambiare_password | boolean | NO | false |
| invito_inviato_at | timestamp with time zone | YES |  |
| totp_obbligatorio | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_risorse_umane_auth_user_django | auth_user_id |
| FOREIGN KEY | fk_risorse_umane_auth_user_risorse_umane | risorsa_umana_id |
| PRIMARY KEY | pk_risorse_umane_auth_user | id |
| UNIQUE | uq_risorse_umane_auth_user_auth_user | auth_user_id |
| UNIQUE | uq_risorse_umane_auth_user_risorsa | risorsa_umana_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_risorse_umane_auth_user | `CREATE UNIQUE INDEX pk_risorse_umane_auth_user ON anagrafiche._legacy_risorse_umane_auth_user USING btree (id)` |
| uq_risorse_umane_auth_user_auth_user | `CREATE UNIQUE INDEX uq_risorse_umane_auth_user_auth_user ON anagrafiche._legacy_risorse_umane_auth_user USING btree (auth_user_id)` |
| uq_risorse_umane_auth_user_risorsa | `CREATE UNIQUE INDEX uq_risorse_umane_auth_user_risorsa ON anagrafiche._legacy_risorse_umane_auth_user USING btree (risorsa_umana_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_risorse_umane_auth_user_a10_guard_persona_fisica_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica()` |
| trg_risorse_umane_auth_user_a10_guard_persona_fisica_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica()` |
| trg_risorse_umane_auth_user_a10_risorse_umane_require_at_5a6f0c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_risorse_umane_auth_user_a10_risorse_umane_require_at_5a6f0c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_risorse_umane_auth_user_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_risorse_umane_auth_user_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_risorse_umane_auth_user_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_risorse_umane_auth_user_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_risorse_umane_auth_user_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('risorse_umane_auth_user_id')` |
| trg_risorse_umane_auth_user_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('risorse_umane_auth_user_id')` |
| trg_risorse_umane_auth_user_z90_sync_auth_user_active_ins | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_sync_active()` |
| trg_risorse_umane_auth_user_z90_sync_auth_user_active_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_sync_active()` |

---
{% include-markdown "signature-core.md" %}
