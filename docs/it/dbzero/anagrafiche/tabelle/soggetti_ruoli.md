{% include-markdown "it/dbzero/anagrafiche/manual/soggetti_ruoli.md" %}
# 📚 Tabella `soggetti_ruoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.soggetti_ruoli_id_seq'::regclass) |
| soggetto_id | uuid | NO |  |
| ruolo_id | integer | NO |  |
| extra | jsonb | YES | '{}'::jsonb |
| user_insert | character varying | NO |  |
| user_update | character varying | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id, soggetto_id, soggetto_id, soggetto_id |
| FOREIGN KEY | fk_tipi_ruoli_config | ruolo_id, ruolo_id |
| PRIMARY KEY | pk_soggetti_ruoli | id |
| UNIQUE | uq_soggetto_ruolo | ruolo_id, soggetto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_soggetti_ruoli_ruolo_id | `CREATE INDEX ix_soggetti_ruoli_ruolo_id ON anagrafiche.soggetti_ruoli USING btree (ruolo_id)` |
| ix_soggetti_ruoli_soggetto_id | `CREATE INDEX ix_soggetti_ruoli_soggetto_id ON anagrafiche.soggetti_ruoli USING btree (soggetto_id)` |
| pk_soggetti_ruoli | `CREATE UNIQUE INDEX pk_soggetti_ruoli ON anagrafiche.soggetti_ruoli USING btree (id)` |
| uq_soggetto_ruolo | `CREATE UNIQUE INDEX uq_soggetto_ruolo ON anagrafiche.soggetti_ruoli USING btree (soggetto_id, ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_ruoli_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ruoli_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_soggetti_ruoli_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
