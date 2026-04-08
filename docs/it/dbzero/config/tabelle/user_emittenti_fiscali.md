{% include-markdown "it/dbzero/config/manual/user_emittenti_fiscali.md" %}
# 📚 Tabella `user_emittenti_fiscali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_user_emittenti_fiscali_emittente | emittente_fiscale_id |
| PRIMARY KEY | pk_user_emittenti_fiscali | id |
| UNIQUE | uq_user_emittenti_fiscali_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_user_emittenti_fiscali_emittente_id | `CREATE INDEX ix_user_emittenti_fiscali_emittente_id ON config.user_emittenti_fiscali USING btree (emittente_fiscale_id)` |
| pk_user_emittenti_fiscali | `CREATE UNIQUE INDEX pk_user_emittenti_fiscali ON config.user_emittenti_fiscali USING btree (id)` |
| uq_user_emittenti_fiscali_auth_user | `CREATE UNIQUE INDEX uq_user_emittenti_fiscali_auth_user ON config.user_emittenti_fiscali USING btree (auth_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_user_emittenti_fiscali_a10_emittenti_fiscali_require_4dae7e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_user_emittenti_fiscali_a10_emittenti_fiscali_require_4dae7e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_user_emittenti_fiscali_a10_guard_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION config.trgfn_user_emittenti_fiscali_guard_delete()` |
| trg_user_emittenti_fiscali_a10_lock_emittente_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('emittente_fiscale_id', 'E_EMITTENTE_NON_MODIFICABILE')` |
| trg_user_emittenti_fiscali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_emittenti_fiscali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('user_emittenti_fiscali_id')` |
| trg_user_emittenti_fiscali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('user_emittenti_fiscali_id')` |

---
{% include-markdown "signature-core.md" %}
