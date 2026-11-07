{% include-markdown "it/dbzero/vendite/manual/fatture.md" %}
# 📚 Tabella `fatture`

> 📝 **Descrizione**
>
> Fatture di vendita (testata). Un documento fiscale per registro/anno/serie/numero; stati e tipi non legati a sistemi nazionali.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| registro_id | bigint | NO |  |
| anno | smallint | YES |  |
| serie | character varying(8) | YES |  |
| numero | bigint | YES |  |
| data | date | NO | script.fn_data_operativa() |
| tipo_doc_fiscale_id | bigint | YES |  |
| stato_doc_fiscale_id | bigint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| reseller_soggetto_ruolo_id | bigint | YES |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric(18,8) | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| imponibile_tot | numeric(18,6) | YES |  |
| imposta_tot | numeric(18,6) | YES |  |
| bollo_applicato | boolean | YES |  |
| bollo_importo | numeric(6,2) | YES |  |
| arrotondamento_precedente | numeric(18,6) | YES |  |
| arrotondamento_attuale | numeric(18,6) | YES |  |
| totale_doc | numeric(18,6) | YES |  |
| minimo | boolean | NO | false |
| data_contabilizzazione | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| termine_pagamento_id | bigint | YES |  |
| termine_pagamento_snapshot | jsonb | YES |  |
| critical | boolean | NO | false |
| totale_a_pagare | numeric | YES |  |
| canale_origine | config.canale_origine | NO | 'ADMIN'::config.canale_origine |
| emittente_snapshot | jsonb | YES |  |
| cliente_snapshot | jsonb | YES |  |
| utility_id | integer | YES |  |
| natura_doc_id | bigint | NO | config.fn_get_natura_doc_fiscale_id('FATTURA'::character varying) |
| competenza_mese | date | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_arrotondamento_attuale_finito |  |
| CHECK | chk_fatture_arrotondamento_precedente_finito |  |
| CHECK | chk_fatture_bollo_importo_finito |  |
| CHECK | chk_fatture_imponibile_tot_finito |  |
| CHECK | chk_fatture_imposta_tot_finito |  |
| CHECK | chk_fatture_sorgente_forma |  |
| CHECK | chk_fatture_tasso_cambio_finito |  |
| CHECK | chk_fatture_totale_a_pagare_finito |  |
| CHECK | chk_fatture_totale_doc_finito |  |
| FOREIGN KEY | fk_fatture_ba | billing_account_id |
| FOREIGN KEY | fk_fatture_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatture_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_fatture_natura_doc | natura_doc_id |
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
| ix_fatture_v_sorgente_id | `CREATE INDEX ix_fatture_v_sorgente_id ON vendite.fatture USING btree (sorgente_tipo_id, sorgente_id) WHERE (sorgente_id IS NOT NULL)` |
| ix_fatture_v_sorgente_uid | `CREATE INDEX ix_fatture_v_sorgente_uid ON vendite.fatture USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_uid IS NOT NULL)` |
| ix_fatture_valuta_id | `CREATE INDEX ix_fatture_valuta_id ON vendite.fatture USING btree (valuta_id)` |
| ix_vendite_fatture_stato_doc_fiscale_id | `CREATE INDEX ix_vendite_fatture_stato_doc_fiscale_id ON vendite.fatture USING btree (stato_doc_fiscale_id)` |
| pk_fatture | `CREATE UNIQUE INDEX pk_fatture ON vendite.fatture USING btree (id)` |
| uq_fatture_numero | `CREATE UNIQUE INDEX uq_fatture_numero ON vendite.fatture USING btree (registro_id, anno, COALESCE(serie, ''::character varying), numero) WHERE (numero IS NOT NULL)` |
| uq_fatture_uid | `CREATE UNIQUE INDEX uq_fatture_uid ON vendite.fatture USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_a05_guard_numero_fiscale_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_numero_fiscale()` |
| trg_fatture_a05_guard_numero_fiscale_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_numero_fiscale()` |
| trg_fatture_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_fiscale_id', 'config.stati_doc_fiscale')` |
| trg_fatture_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_fatture_a10_guard_data_numerata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_data_numerata()` |
| trg_fatture_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_fatture_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_fatture_a10_guard_intestazione_congelata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('id')` |
| trg_fatture_a10_guard_registro_emittente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_registro_emittente()` |
| trg_fatture_a10_guard_registro_emittente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_registro_emittente()` |
| trg_fatture_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_fatture_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_fatture_a10_guard_stato_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_stato()` |
| trg_fatture_a10_guard_uscita_draft_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_guard_uscita_draft()` |
| trg_fatture_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('natura_doc_id', 'E_COLONNA_NON_MODIFICABILE')` |
| trg_fatture_a10_nature_doc_fiscale_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_fatture_a10_nature_doc_fiscale_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_fatture_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_fatture_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_fatture_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_fatture_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_fatture_a10_stati_doc_fiscale_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatture_a10_stati_doc_fiscale_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatture_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fatture_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fatture_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatture_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatture_a11_numerata_non_annulabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_numerata_non_annulabile()` |
| trg_fatture_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_def_guard_stato_lotto_coerente_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_lotto_fatture_guard_stato_coerente()` |
| trg_fatture_def_guard_stato_lotto_coerente_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_lotto_fatture_guard_stato_coerente()` |
| trg_fatture_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_id')` |
| trg_fatture_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_id')` |
| trg_vendite_fatture_a10_canale_origine_immutable_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_canale_origine_immutable()` |
| trg_vendite_fatture_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
