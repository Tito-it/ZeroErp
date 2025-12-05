# 📚 Tabella `vettori`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

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
| ix_vettori_codice_upper | `CREATE INDEX ix_vettori_codice_upper ON anagrafiche.vettori USING btree (upper((codice)::text))` |
| pk_vettori | `CREATE UNIQUE INDEX pk_vettori ON anagrafiche.vettori USING btree (id)` |
| uq_vettori_codice | `CREATE UNIQUE INDEX uq_vettori_codice ON anagrafiche.vettori USING btree (codice)` |
| uq_vettori_ruolo | `CREATE UNIQUE INDEX uq_vettori_ruolo ON anagrafiche.vettori USING btree (soggetto_ruolo_id)` |
| uq_vettori_uid | `CREATE UNIQUE INDEX uq_vettori_uid ON anagrafiche.vettori USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vettori_a10_protect_codice_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_protect_codice()` |
| trg_vettori_guard_ruolo_vettore_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_guard_ruolo_vettore()` |
| trg_vettori_guard_ruolo_vettore_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_guard_ruolo_vettore()` |
| trg_vettori_norm_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_normalize()` |
| trg_vettori_norm_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_vettori_normalize()` |

---
{% include-markdown "signature-core.md" %}
