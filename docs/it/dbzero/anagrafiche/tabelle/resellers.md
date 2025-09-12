# 📚 Tabella `resellers`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | gen_random_uuid() |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_resellers_codice_non_vuoto |  |
| FOREIGN KEY | fk_resellers_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_resellers | id |
| UNIQUE | uq_resellers_codice | codice |
| UNIQUE | uq_resellers_ruolo | soggetto_ruolo_id |
| UNIQUE | uq_resellers_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resellers_attivo | `CREATE INDEX ix_resellers_attivo ON anagrafiche.resellers USING btree (attivo)` |
| ix_resellers_codice_upper | `CREATE INDEX ix_resellers_codice_upper ON anagrafiche.resellers USING btree (upper((codice)::text))` |
| pk_resellers | `CREATE UNIQUE INDEX pk_resellers ON anagrafiche.resellers USING btree (id)` |
| uq_resellers_codice | `CREATE UNIQUE INDEX uq_resellers_codice ON anagrafiche.resellers USING btree (codice)` |
| uq_resellers_ruolo | `CREATE UNIQUE INDEX uq_resellers_ruolo ON anagrafiche.resellers USING btree (soggetto_ruolo_id)` |
| uq_resellers_uid | `CREATE UNIQUE INDEX uq_resellers_uid ON anagrafiche.resellers USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_resellers_upd_protect_codice | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_a10_resellers_protect_codice()` |
| trg_resellers_ins_upd_check_ruolo_reseller | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_ins_upd_check_ruolo_reseller()` |
| trg_resellers_ins_upd_check_ruolo_reseller | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_ins_upd_check_ruolo_reseller()` |
| trg_resellers_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resellers_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resellers_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_norm()` |
| trg_resellers_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_norm()` |
| trg_upd_resellers_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_resellers_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('resellers_id')` |
| trg_z90_resellers_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('resellers_id')` |

---
{% include-markdown "signature-core.md" %}
