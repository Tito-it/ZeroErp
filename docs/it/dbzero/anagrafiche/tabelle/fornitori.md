{% include-markdown "it/dbzero/anagrafiche/manual/fornitori.md" %}
# 📚 Tabella `fornitori`

> 📝 **Descrizione**
>
> Master FORNITORE (1:1 con soggetti_ruoli): configurazione fiscale, operativa e qualità.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| codice | character varying(32) | NO |  |
| attivo | boolean | NO | true |
| valuta_id | integer | YES |  |
| modalita_pagamento_id | integer | YES |  |
| giorni_pagamento | smallint | YES |  |
| fine_mese | boolean | YES |  |
| split_payment | boolean | YES |  |
| ritenuta_acconto | boolean | YES |  |
| ritenuta_aliquota | numeric(5,2) | YES |  |
| regime_fiscale | character varying(8) | YES |  |
| bollo_esente | boolean | YES |  |
| canale_fe | character varying(7) | YES |  |
| pec_email | character varying(256) | YES |  |
| rating | smallint | YES |  |
| qualifica_scadenza | date | YES |  |
| note | text | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| uid | uuid | NO | uuidv7() |
| stato_fornitore_id | integer | NO |  |
| termine_pagamento_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fornitori_canale_fe_len |  |
| CHECK | chk_fornitori_rating |  |
| CHECK | chk_fornitori_ritenuta_aliquota |  |
| CHECK | chk_fornitori_ritenuta_aliquota_finito |  |
| FOREIGN KEY | fk_fornitori_modalita_pagamento | modalita_pagamento_id |
| FOREIGN KEY | fk_fornitori_soggetti_ruoli | soggetto_ruolo_id |
| FOREIGN KEY | fk_fornitori_stati_fornitore | stato_fornitore_id |
| FOREIGN KEY | fk_fornitori_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_fornitori_valute | valuta_id |
| PRIMARY KEY | pk_fornitori | id |
| UNIQUE | uq_fornitori_codice | codice |
| UNIQUE | uq_fornitori_soggetto_ruolo_id | soggetto_ruolo_id |
| UNIQUE | uq_fornitori_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fornitori_attivo_stato | `CREATE INDEX ix_fornitori_attivo_stato ON anagrafiche.fornitori USING btree (attivo, stato_fornitore_id)` |
| ix_fornitori_codice_trgm | `CREATE INDEX ix_fornitori_codice_trgm ON anagrafiche.fornitori USING gin (codice gin_trgm_ops)` |
| pk_fornitori | `CREATE UNIQUE INDEX pk_fornitori ON anagrafiche.fornitori USING btree (id)` |
| uq_fornitori_codice | `CREATE UNIQUE INDEX uq_fornitori_codice ON anagrafiche.fornitori USING btree (codice)` |
| uq_fornitori_soggetto_ruolo_id | `CREATE UNIQUE INDEX uq_fornitori_soggetto_ruolo_id ON anagrafiche.fornitori USING btree (soggetto_ruolo_id)` |
| uq_fornitori_uid | `CREATE UNIQUE INDEX uq_fornitori_uid ON anagrafiche.fornitori USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fornitori_a10_delete_block_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_fornitori_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_gen_codice()` |
| trg_fornitori_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_gen_codice()` |
| trg_fornitori_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE')` |
| trg_fornitori_a10_stati_fornitore_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_fornitore', 'attivo', 'stato_fornitore_id', 'id')` |
| trg_fornitori_a10_stati_fornitore_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_fornitore', 'attivo', 'stato_fornitore_id', 'id')` |
| trg_fornitori_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fornitori_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fornitori_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_fornitori_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_fornitori_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fornitori_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fornitori_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fornitori_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fornitori_guard_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()` |
| trg_fornitori_guard_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()` |
| trg_fornitori_guard_ruolo_fornitore_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()` |
| trg_fornitori_guard_ruolo_fornitore_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()` |
| trg_fornitori_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fornitori_id')` |
| trg_fornitori_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fornitori_id')` |

---
{% include-markdown "signature-core.md" %}
