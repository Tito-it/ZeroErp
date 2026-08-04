# 📚 Tabella `user_emittente_attivo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_user_emittente_attivo_emittente | emittente_fiscale_id |
| PRIMARY KEY | pk_user_emittente_attivo | id |
| UNIQUE | uq_user_emittente_attivo_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_user_emittente_attivo | `CREATE UNIQUE INDEX pk_user_emittente_attivo ON config.user_emittente_attivo USING btree (id)` |
| uq_user_emittente_attivo_auth_user | `CREATE UNIQUE INDEX uq_user_emittente_attivo_auth_user ON config.user_emittente_attivo USING btree (auth_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_user_emittente_attivo_a10_emittenti_fiscali_require__83f6ad | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_user_emittente_attivo_a10_emittenti_fiscali_require__83f6ad | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_user_emittente_attivo_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_emittente_attivo_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_user_emittente_attivo_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_emittente_attivo_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
