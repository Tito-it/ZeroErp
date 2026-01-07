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
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

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
| pk_fornitori | `CREATE UNIQUE INDEX pk_fornitori ON anagrafiche.fornitori USING btree (id)` |
| uq_fornitori_codice | `CREATE UNIQUE INDEX uq_fornitori_codice ON anagrafiche.fornitori USING btree (codice)` |
| uq_fornitori_soggetto_ruolo_id | `CREATE UNIQUE INDEX uq_fornitori_soggetto_ruolo_id ON anagrafiche.fornitori USING btree (soggetto_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fornitori_a10_protect_account_code_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_protect_account_code()` |
| trg_fornitori_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fornitori_guard_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()` |
| trg_fornitori_guard_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()` |
| trg_fornitori_guard_ruolo_fornitore_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()` |
| trg_fornitori_guard_ruolo_fornitore_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()` |
| trg_fornitori_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fornitori_id')` |
| trg_fornitori_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fornitori_id')` |

---
{% include-markdown "signature-core.md" %}
