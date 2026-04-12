{% include-markdown "it/dbzero/vendite/manual/listini_associazioni.md" %}
# 📚 Tabella `listini_associazioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| listino_id | bigint | NO |  |
| billing_account_id | bigint | YES |  |
| utility_id | integer | YES |  |
| emittente_soggetto_ruolo_id | bigint | YES |  |
| valido_dal | date | NO | CURRENT_DATE |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_associazioni_date |  |
| FOREIGN KEY | fk_listini_associazioni_ba | billing_account_id |
| FOREIGN KEY | fk_listini_associazioni_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_listini_associazioni_listino | listino_id |
| FOREIGN KEY | fk_listini_associazioni_utility | utility_id |
| PRIMARY KEY | pk_listini_associazioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_listini_associazioni_no_overlap | `CREATE INDEX ex_listini_associazioni_no_overlap ON vendite.listini_associazioni USING gist (COALESCE(billing_account_id, (- (1)::bigint)), COALESCE(utility_id, (- 1)), COALESCE(emittente_soggetto_ruolo_id, (- (1)::bigint)), validita) WHERE (attivo IS TRUE)` |
| pk_listini_associazioni | `CREATE UNIQUE INDEX pk_listini_associazioni ON vendite.listini_associazioni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_associazioni_a10_listini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_listini_associazioni_a10_listini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_listini_associazioni_a20_set_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_set_validita()` |
| trg_listini_associazioni_a20_set_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_set_validita()` |
| trg_listini_associazioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_associazioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_associazioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_associazioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
