{% include-markdown "it/dbzero/anagrafiche/manual/resellers.md" %}
# 📚 Tabella `resellers`

> 📝 **Descrizione**
>
> Ruolo RES (rivenditori/reseller). Metadati generici, FK 1:1 al soggetto_ruolo.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

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
| pk_resellers | `CREATE UNIQUE INDEX pk_resellers ON anagrafiche.resellers USING btree (id)` |
| uq_resellers_codice | `CREATE UNIQUE INDEX uq_resellers_codice ON anagrafiche.resellers USING btree (codice)` |
| uq_resellers_ruolo | `CREATE UNIQUE INDEX uq_resellers_ruolo ON anagrafiche.resellers USING btree (soggetto_ruolo_id)` |
| uq_resellers_uid | `CREATE UNIQUE INDEX uq_resellers_uid ON anagrafiche.resellers USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resellers_a10_delete_block_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_resellers_a10_guard_attivo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_guard_attivo()` |
| trg_resellers_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE')` |
| trg_resellers_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_resellers_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_resellers_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resellers_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resellers_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resellers_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resellers_guard_ruolo_reseller_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_guard_ruolo_reseller()` |
| trg_resellers_guard_ruolo_reseller_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_guard_ruolo_reseller()` |
| trg_resellers_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_normalize()` |
| trg_resellers_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_resellers_normalize()` |
| trg_resellers_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('resellers_id')` |
| trg_resellers_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('resellers_id')` |

---
{% include-markdown "signature-core.md" %}
