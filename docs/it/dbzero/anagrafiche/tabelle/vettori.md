{% include-markdown "it/dbzero/anagrafiche/manual/vettori.md" %}
# 📚 Tabella `vettori`

> 📝 **Descrizione**
>
> Ruolo RES (rivenditori/vettore). Metadati generici, FK 1:1 al soggetto_ruolo.

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
| CHECK | chk_vettori_codice_non_vuoto |  |
| FOREIGN KEY | fk_vettori_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_vettori | id |
| UNIQUE | uq_vettori_codice | codice |
| UNIQUE | uq_vettori_ruolo | soggetto_ruolo_id |
| UNIQUE | uq_vettori_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vettori_attivo | `CREATE INDEX ix_vettori_attivo ON anagrafiche.vettori USING btree (attivo)` |
| ix_vettori_codice_trgm | `CREATE INDEX ix_vettori_codice_trgm ON anagrafiche.vettori USING gin (codice gin_trgm_ops)` |
| pk_vettori | `CREATE UNIQUE INDEX pk_vettori ON anagrafiche.vettori USING btree (id)` |
| uq_vettori_codice | `CREATE UNIQUE INDEX uq_vettori_codice ON anagrafiche.vettori USING btree (codice)` |
| uq_vettori_ruolo | `CREATE UNIQUE INDEX uq_vettori_ruolo ON anagrafiche.vettori USING btree (soggetto_ruolo_id)` |
| uq_vettori_uid | `CREATE UNIQUE INDEX uq_vettori_uid ON anagrafiche.vettori USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vettori_a10_delete_block_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_vettori_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_gen_codice()` |
| trg_vettori_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_gen_codice()` |
| trg_vettori_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE')` |
| trg_vettori_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vettori_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vettori_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vettori_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vettori_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vettori_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vettori_guard_ruolo_vettore_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_guard_ruolo_vettore()` |
| trg_vettori_guard_ruolo_vettore_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_guard_ruolo_vettore()` |
| trg_vettori_norm_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_normalize()` |
| trg_vettori_norm_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_normalize()` |
| trg_vettori_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('vettori_id')` |
| trg_vettori_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('vettori_id')` |

---
{% include-markdown "signature-core.md" %}
