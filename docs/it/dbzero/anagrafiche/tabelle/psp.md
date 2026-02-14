{% include-markdown "it/dbzero/anagrafiche/manual/psp.md" %}
# 📚 Tabella `psp`

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
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_psp_codice_non_vuoto |  |
| FOREIGN KEY | fk_psp_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_psp | id |
| UNIQUE | uq_psp_codice | codice |
| UNIQUE | uq_psp_ruolo | soggetto_ruolo_id |
| UNIQUE | uq_psp_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_psp_attivo | `CREATE INDEX ix_psp_attivo ON anagrafiche.psp USING btree (attivo)` |
| pk_psp | `CREATE UNIQUE INDEX pk_psp ON anagrafiche.psp USING btree (id)` |
| uq_psp_codice | `CREATE UNIQUE INDEX uq_psp_codice ON anagrafiche.psp USING btree (codice)` |
| uq_psp_ruolo | `CREATE UNIQUE INDEX uq_psp_ruolo ON anagrafiche.psp USING btree (soggetto_ruolo_id)` |
| uq_psp_uid | `CREATE UNIQUE INDEX uq_psp_uid ON anagrafiche.psp USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_psp_guard_ruolo_psp_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_psp_guard_ruolo_psp()` |
| trg_psp_guard_ruolo_psp_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_psp_guard_ruolo_psp()` |

---
{% include-markdown "signature-core.md" %}
