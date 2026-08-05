{% include-markdown "it/dbzero/vendite/manual/fatture.md" %}
# 📚 Tabella `fatture`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| registro_id | bigint | NO |  |
| anno | smallint | YES |  |
| serie | character varying | YES |  |
| numero | bigint | YES |  |
| data | date | NO | CURRENT_DATE |
| tipo_doc_fiscale_id | bigint | YES |  |
| stato_doc_fiscale_id | bigint | YES |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| reseller_soggetto_ruolo_id | bigint | YES |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| imponibile_tot | numeric | YES |  |
| imposta_tot | numeric | YES |  |
| bollo_applicato | boolean | YES |  |
| bollo_importo | numeric | YES |  |
| arrotondamento_precedente | numeric | YES |  |
| arrotondamento_attuale | numeric | YES |  |
| totale_doc | numeric | YES |  |
| minimo | boolean | NO | false |
| data_contabilizzazione | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| termine_pagamento_id | bigint | YES |  |
| termine_pagamento_snapshot | jsonb | YES |  |
| critical | boolean | NO | false |
| totale_a_pagare | numeric | YES |  |
| canale_origine | USER-DEFINED | NO | 'ADMIN'::config.canale_origine |
| emittente_snapshot | jsonb | YES |  |
| cliente_snapshot | jsonb | YES |  |
| utility_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_ba | billing_account_id |
| FOREIGN KEY | fk_fatture_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatture_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_fatture_registro | registro_id |
| FOREIGN KEY | fk_fatture_reseller | reseller_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatture_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_fatture_stato_doc_fiscale | stato_doc_fiscale_id |
| FOREIGN KEY | fk_fatture_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_fatture_tipo_doc_fiscale | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_fatture_utility | utility_id |
| FOREIGN KEY | fk_fatture_valuta | valuta_id |
| PRIMARY KEY | pk_fatture | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_ba_data | `CREATE INDEX ix_fatture_ba_data ON vendite.fatture USING btree (billing_account_id, data)` |
| ix_fatture_data_contabile | `CREATE INDEX ix_fatture_data_contabile ON vendite.fatture USING btree (data_contabilizzazione)` |
| ix_fatture_emitt_data | `CREATE INDEX ix_fatture_emitt_data ON vendite.fatture USING btree (emittente_soggetto_ruolo_id, data)` |
| ix_fatture_modalita_pagamento_id | `CREATE INDEX ix_fatture_modalita_pagamento_id ON vendite.fatture USING btree (modalita_pagamento_id)` |
| ix_fatture_registro_id | `CREATE INDEX ix_fatture_registro_id ON vendite.fatture USING btree (registro_id)` |
| ix_fatture_reseller_soggetto_ruolo_id | `CREATE INDEX ix_fatture_reseller_soggetto_ruolo_id ON vendite.fatture USING btree (reseller_soggetto_ruolo_id)` |
| ix_fatture_sorgente_tipo_id | `CREATE INDEX ix_fatture_sorgente_tipo_id ON vendite.fatture USING btree (sorgente_tipo_id)` |
| ix_fatture_termine_pagamento_id | `CREATE INDEX ix_fatture_termine_pagamento_id ON vendite.fatture USING btree (termine_pagamento_id)` |
| ix_fatture_tipo_doc_fiscale_id | `CREATE INDEX ix_fatture_tipo_doc_fiscale_id ON vendite.fatture USING btree (tipo_doc_fiscale_id)` |
| ix_fatture_valuta_id | `CREATE INDEX ix_fatture_valuta_id ON vendite.fatture USING btree (valuta_id)` |
| ix_vendite_fatture_stato_doc_fiscale_id | `CREATE INDEX ix_vendite_fatture_stato_doc_fiscale_id ON vendite.fatture USING btree (stato_doc_fiscale_id)` |
| pk_fatture | `CREATE UNIQUE INDEX pk_fatture ON vendite.fatture USING btree (id)` |
| uq_fatture_numero | `CREATE UNIQUE INDEX uq_fatture_numero ON vendite.fatture USING btree (registro_id, anno, COALESCE(serie, ''::character varying), numero) WHERE (numero IS NOT NULL)` |
| uq_fatture_uid | `CREATE UNIQUE INDEX uq_fatture_uid ON vendite.fatture USING btree (uid)` |
| uq_fatture_v_sorgente_fk | `CREATE UNIQUE INDEX uq_fatture_v_sorgente_fk ON vendite.fatture USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_fatture_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_fatture_a10_guard_intestazione_congelata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('id')` |
| trg_fatture_a10_guard_stato_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_stato()` |
| trg_fatture_a10_guard_uscita_draft_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_uscita_draft()` |
| trg_fatture_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_fatture_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_fatture_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_fatture_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_fatture_a10_stati_doc_fiscale_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatture_a10_stati_doc_fiscale_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatture_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fatture_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fatture_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatture_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatture_a11_numerata_non_annulabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_numerata_non_annulabile()` |
| trg_fatture_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_def_guard_stato_lotto_coerente_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_lotto_fatture_guard_stato_coerente()` |
| trg_fatture_def_guard_stato_lotto_coerente_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_lotto_fatture_guard_stato_coerente()` |
| trg_fatture_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_id')` |
| trg_fatture_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_id')` |
| trg_vendite_fatture_a10_canale_origine_immutable_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_canale_origine_immutable()` |

---
{% include-markdown "signature-core.md" %}
