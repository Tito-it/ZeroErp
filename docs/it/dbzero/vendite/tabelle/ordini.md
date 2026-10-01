{% include-markdown "it/dbzero/vendite/manual/ordini.md" %}
# 📚 Tabella `ordini`

> 📝 **Descrizione**
>
> Ordini di vendita (testata) con campi già utili alla futura emissione di DDT.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | bigint | YES |  |
| serie | character varying | YES |  |
| numero | character varying | YES |  |
| anno | smallint | YES |  |
| data | date | NO | CURRENT_DATE |
| stato_doc_ordine_id | bigint | NO |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| imponibile_tot | numeric | YES |  |
| sconto_tot | numeric | YES |  |
| iva_tot | numeric | YES |  |
| totale_doc | numeric | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| termine_pagamento_id | bigint | YES |  |
| fatturazione_trigger | character varying | NO |  |
| canale_origine | USER-DEFINED | NO | 'ADMIN'::config.canale_origine |
| utility_id | integer | YES |  |
| emittente_fiscale_id | bigint | NO |  |
| agente_soggetto_ruolo_id | bigint | YES |  |
| documento_origine_tipo | character varying | YES |  |
| documento_origine_id | bigint | YES |  |
| fatturazione_immediata | boolean | NO | false |
| registro_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_documento_origine_copres |  |
| CHECK | chk_ordini_documento_origine_tipo |  |
| CHECK | chk_ordini_fatturazione_trigger |  |
| FOREIGN KEY | fk_ordini_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_ordini_registro | registro_id |
| FOREIGN KEY | fk_ordini_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_ordini_v_agente_ruolo | agente_soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_v_billing_account | billing_account_id |
| FOREIGN KEY | fk_ordini_v_cliente_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_v_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_ordini_v_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ordini_v_stato_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordini_v_utility | utility_id |
| FOREIGN KEY | fk_ordini_v_valute | valuta_id |
| PRIMARY KEY | pk_ordini | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_emittente_fiscale_id | `CREATE INDEX ix_ordini_emittente_fiscale_id ON vendite.ordini USING btree (emittente_fiscale_id)` |
| ix_ordini_id_text | `CREATE INDEX ix_ordini_id_text ON vendite.ordini USING btree (((id)::text))` |
| ix_ordini_v_cliente_statoid_data | `CREATE INDEX ix_ordini_v_cliente_statoid_data ON vendite.ordini USING btree (soggetto_ruolo_id, stato_doc_ordine_id, data)` |
| ix_vendite_ordini_stato_doc_ordine_id | `CREATE INDEX ix_vendite_ordini_stato_doc_ordine_id ON vendite.ordini USING btree (stato_doc_ordine_id)` |
| pk_ordini | `CREATE UNIQUE INDEX pk_ordini ON vendite.ordini USING btree (id)` |
| uq_ordini_v_anno_serie_numero | `CREATE UNIQUE INDEX uq_ordini_v_anno_serie_numero ON vendite.ordini USING btree (registro_id, anno, serie, numero) NULLS NOT DISTINCT WHERE (numero IS NOT NULL)` |
| uq_ordini_v_documento_origine_offerta | `CREATE UNIQUE INDEX uq_ordini_v_documento_origine_offerta ON vendite.ordini USING btree (documento_origine_tipo, documento_origine_id) WHERE ((documento_origine_tipo)::text = 'OFFERTA'::text)` |
| uq_ordini_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_v_sorgente_fk ON vendite.ordini USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |
| uq_ordini_v_uid | `CREATE UNIQUE INDEX uq_ordini_v_uid ON vendite.ordini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_ordini_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_ordini_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_ordini_a10_gen_numero_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_gen_numero()` |
| trg_ordini_a10_guard_chiusura_sorgente_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_chiusura_sorgente('ORDINE_VENDITA', 'stato_doc_ordine_id', 'config.stati_doc_ordini')` |
| trg_ordini_a10_guard_delete_solo_bozza_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()` |
| trg_ordini_a10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_guard_emittente_ba()` |
| trg_ordini_a10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_guard_emittente_ba()` |
| trg_ordini_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_ordini_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_ordini_a10_guard_fatt_immediata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('ORDINE_VENDITA')` |
| trg_ordini_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_guard_transizione()` |
| trg_ordini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('billing_account_id', 'E_ORD_CLIENTE_IMMUTABILE', 'numero', 'E_CODICE_NON_MODIFICABILE', 'soggetto_ruolo_id', 'E_ORD_CLIENTE_IMMUTABILE')` |
| trg_ordini_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_ordini_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_ordini_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_ordini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_normalize()` |
| trg_ordini_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_normalize()` |
| trg_ordini_z90_ricalcola_totali_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_ricalcola_totali()` |
| trg_ordini_z90_ritira_commessa_attivita_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_ritira_commessa_attivita('ORDINE_VENDITA', 'stato_doc_ordine_id', 'config.stati_doc_ordini')` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |
| trg_ordini_z90_sync_canali_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |
| trg_ordini_z90_sync_canali_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |
| trg_vendite_ordini_a10_canale_origine_immutable_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_canale_origine_immutable()` |

---
{% include-markdown "signature-core.md" %}
