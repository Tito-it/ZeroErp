{% include-markdown "it/dbzero/config/manual/user_override_aree.md" %}
# 📚 Tabella `user_override_aree`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| area_id | integer | NO |  |
| livello | USER-DEFINED | NO |  |
| motivo | text | YES |  |
| valido_dal | date | YES | CURRENT_DATE |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_user_override_aree_validita |  |
| FOREIGN KEY | fk_user_override_aree_area | area_id |
| PRIMARY KEY | pk_user_override_aree | id |
| UNIQUE | uq_user_override_aree_user_area | auth_user_id, area_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_user_override_aree_area_id | `CREATE INDEX ix_user_override_aree_area_id ON config.user_override_aree USING btree (area_id)` |
| ix_user_override_aree_auth_user_id | `CREATE INDEX ix_user_override_aree_auth_user_id ON config.user_override_aree USING btree (auth_user_id)` |
| pk_user_override_aree | `CREATE UNIQUE INDEX pk_user_override_aree ON config.user_override_aree USING btree (id)` |
| uq_user_override_aree_user_area | `CREATE UNIQUE INDEX uq_user_override_aree_user_area ON config.user_override_aree USING btree (auth_user_id, area_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_user_override_aree_a10_aree_funzionali_require_attiv_bb335d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id')` |
| trg_user_override_aree_a10_aree_funzionali_require_attiv_bb335d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id')` |
| trg_user_override_aree_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_override_aree_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
