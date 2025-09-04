{% include-markdown "it/dbzero/anagrafiche/manual/fornitori.md" %}
# 📚 Tabella `fornitori`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying | YES |  |
| attivo | boolean | NO | true |
| stato_operativo | character varying | YES |  |
| valuta_id | integer | YES |  |
| modalita_pagamento_id | integer | YES |  |
| giorni_pagamento | smallint | YES |  |
| fine_mese | boolean | YES |  |
| split_payment | boolean | YES |  |
| ritenuta_acconto | boolean | YES |  |
| ritenuta_aliquota | numeric | YES |  |
| regime_fiscale | character varying | YES |  |
| bollo_esente | boolean | YES |  |
| canale_fe | character varying | YES |  |
| pec_email | character varying | YES |  |
| rating | smallint | YES |  |
| qualifica_scadenza | date | YES |  |
| note | text | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fornitori_canale_fe_len |  |
| CHECK | chk_fornitori_rating |  |
| CHECK | chk_fornitori_ritenuta_aliquota |  |
| FOREIGN KEY | fk_fornitori_modalita_pagamento | modalita_pagamento_id |
| FOREIGN KEY | fk_fornitori_soggetti_ruoli | soggetto_ruolo_id |
| FOREIGN KEY | fk_fornitori_valute | valuta_id |
| PRIMARY KEY | pk_fornitori | id |
| UNIQUE | uq_fornitori_codice | codice |
| UNIQUE | uq_fornitori_soggetto_ruolo_id | soggetto_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fornitori_attivo_stato | `CREATE INDEX ix_fornitori_attivo_stato ON anagrafiche.fornitori USING btree (attivo, stato_operativo)` |
| ix_fornitori_codice | `CREATE INDEX ix_fornitori_codice ON anagrafiche.fornitori USING btree (codice)` |
| ix_fornitori_soggetto_ruolo_id | `CREATE INDEX ix_fornitori_soggetto_ruolo_id ON anagrafiche.fornitori USING btree (soggetto_ruolo_id)` |
| pk_fornitori | `CREATE UNIQUE INDEX pk_fornitori ON anagrafiche.fornitori USING btree (id)` |
| uq_fornitori_codice | `CREATE UNIQUE INDEX uq_fornitori_codice ON anagrafiche.fornitori USING btree (codice)` |
| uq_fornitori_soggetto_ruolo_id | `CREATE UNIQUE INDEX uq_fornitori_soggetto_ruolo_id ON anagrafiche.fornitori USING btree (soggetto_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_fornitori_upd_protect_account_code | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_upd_protect_account_code()` |
| trg_fornitori_ins_upd_check_ruolo_fornitore | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_ins_upd_check_ruolo_fornitore()` |
| trg_fornitori_ins_upd_check_ruolo_fornitore | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_ins_upd_check_ruolo_fornitore()` |
| trg_fornitori_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fornitori_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fornitori_ins_upd_guard_normalize | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()` |
| trg_fornitori_ins_upd_guard_normalize | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()` |
| trg_upd_fornitori_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_fornitori_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('fornitori_id')` |
| trg_z90_fornitori_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('fornitori_id')` |

---
{% include-markdown "signature-core.md" %}
