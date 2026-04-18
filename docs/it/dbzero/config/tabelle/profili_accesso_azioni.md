{% include-markdown "it/dbzero/config/manual/profili_accesso_azioni.md" %}
# 📚 Tabella `profili_accesso_azioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| profilo_accesso_id | integer | NO |  |
| azione_id | integer | NO |  |
| abilitata | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_profili_accesso_azioni_azione | azione_id |
| FOREIGN KEY | fk_profili_accesso_azioni_profilo | profilo_accesso_id |
| PRIMARY KEY | pk_profili_accesso_azioni | id |
| UNIQUE | uq_profili_accesso_azioni_profilo_azione | profilo_accesso_id, azione_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_profili_accesso_azioni | `CREATE UNIQUE INDEX pk_profili_accesso_azioni ON config.profili_accesso_azioni USING btree (id)` |
| uq_profili_accesso_azioni_profilo_azione | `CREATE UNIQUE INDEX uq_profili_accesso_azioni_profilo_azione ON config.profili_accesso_azioni USING btree (profilo_accesso_id, azione_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_profili_accesso_azioni_a10_azioni_processo_require_a_8dec3b | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'azioni_processo', 'attivo', 'azione_id', 'id')` |
| trg_profili_accesso_azioni_a10_azioni_processo_require_a_8dec3b | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'azioni_processo', 'attivo', 'azione_id', 'id')` |
| trg_profili_accesso_azioni_a10_profili_accesso_require_a_4c009c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'profili_accesso', 'attivo', 'profilo_accesso_id', 'id')` |
| trg_profili_accesso_azioni_a10_profili_accesso_require_a_4c009c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'profili_accesso', 'attivo', 'profilo_accesso_id', 'id')` |
| trg_profili_accesso_azioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_azioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_azioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_azioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_azioni_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_azioni_id')` |
| trg_profili_accesso_azioni_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_azioni_id')` |

---
{% include-markdown "signature-core.md" %}
