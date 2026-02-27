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
| priorita | smallint | NO | 100 |
| valido_dal | date | NO | CURRENT_DATE |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_associazioni_date |  |
| CHECK | chk_listini_associazioni_priorita |  |
| FOREIGN KEY | fk_listini_associazioni_ba | billing_account_id |
| FOREIGN KEY | fk_listini_associazioni_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_listini_associazioni_listino | listino_id |
| FOREIGN KEY | fk_listini_associazioni_utility | utility_id |
| PRIMARY KEY | pk_listini_associazioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_listini_associazioni_lookup | `CREATE INDEX ix_listini_associazioni_lookup ON vendite.listini_associazioni USING btree (billing_account_id, utility_id, emittente_soggetto_ruolo_id, priorita) WHERE (attivo IS TRUE)` |
| pk_listini_associazioni | `CREATE UNIQUE INDEX pk_listini_associazioni ON vendite.listini_associazioni USING btree (id)` |
| uq_listini_associazioni_key_attiva | `CREATE UNIQUE INDEX uq_listini_associazioni_key_attiva ON vendite.listini_associazioni USING btree (listino_id, COALESCE(billing_account_id, ('-1'::integer)::bigint), COALESCE(utility_id, '-1'::integer), COALESCE(emittente_soggetto_ruolo_id, ('-1'::integer)::bigint), valido_dal) WHERE (attivo IS TRUE)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_associazioni_a10_listini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id')` |
| trg_listini_associazioni_a10_listini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id')` |
| trg_listini_associazioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_associazioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_associazioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_associazioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
