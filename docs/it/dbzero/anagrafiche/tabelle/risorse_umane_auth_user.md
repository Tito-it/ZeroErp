{% include-markdown "it/dbzero/anagrafiche/manual/risorse_umane_auth_user.md" %}
# 📚 Tabella `risorse_umane_auth_user`

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
| ix_risorse_umane_auth_user_auth_user | `CREATE INDEX ix_risorse_umane_auth_user_auth_user ON anagrafiche.risorse_umane_auth_user USING btree (auth_user_id)` |
| ix_risorse_umane_auth_user_risorsa | `CREATE INDEX ix_risorse_umane_auth_user_risorsa ON anagrafiche.risorse_umane_auth_user USING btree (risorsa_umana_id)` |
| pk_risorse_umane_auth_user | `CREATE UNIQUE INDEX pk_risorse_umane_auth_user ON anagrafiche.risorse_umane_auth_user USING btree (id)` |
| uq_risorse_umane_auth_user_auth_user | `CREATE UNIQUE INDEX uq_risorse_umane_auth_user_auth_user ON anagrafiche.risorse_umane_auth_user USING btree (auth_user_id)` |
| uq_risorse_umane_auth_user_risorsa | `CREATE UNIQUE INDEX uq_risorse_umane_auth_user_risorsa ON anagrafiche.risorse_umane_auth_user USING btree (risorsa_umana_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_risorse_umane_auth_user_a10_guard_gestore_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_gestore()` |
| trg_risorse_umane_auth_user_a10_guard_gestore_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_gestore()` |
| trg_risorse_umane_auth_user_a10_risorse_umane_require_at_5a6f0c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id')` |
| trg_risorse_umane_auth_user_a10_risorse_umane_require_at_5a6f0c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id')` |
| trg_risorse_umane_auth_user_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
