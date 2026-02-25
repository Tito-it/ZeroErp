{% include-markdown "it/dbzero/vendite/manual/ordini.md" %}
# 📚 Tabella `ordini`

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
| fatturazione_trigger | character varying | NO | 'CONFERMATO'::character varying |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_fatturazione_trigger |  |
| FOREIGN KEY | fk_ordini_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_ordini_v_billing_account | billing_account_id |
| FOREIGN KEY | fk_ordini_v_cliente_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_v_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_ordini_v_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ordini_v_stato_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordini_v_valute | valuta_id |
| PRIMARY KEY | pk_ordini | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_v_cliente_statoid_data | `CREATE INDEX ix_ordini_v_cliente_statoid_data ON vendite.ordini USING btree (soggetto_ruolo_id, stato_doc_ordine_id, data)` |
| ix_vendite_ordini_stato_doc_ordine_id | `CREATE INDEX ix_vendite_ordini_stato_doc_ordine_id ON vendite.ordini USING btree (stato_doc_ordine_id)` |
| pk_ordini | `CREATE UNIQUE INDEX pk_ordini ON vendite.ordini USING btree (id)` |
| uq_ordini_v_anno_serie_numero | `CREATE UNIQUE INDEX uq_ordini_v_anno_serie_numero ON vendite.ordini USING btree (anno, serie, numero) WHERE (numero IS NOT NULL)` |
| uq_ordini_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_v_sorgente_fk ON vendite.ordini USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |
| uq_ordini_v_uid | `CREATE UNIQUE INDEX uq_ordini_v_uid ON vendite.ordini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_gen_codice()` |
| trg_ordini_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_gen_codice()` |
| trg_ordini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'CODICE_NON_MODIFICABILE')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id')` |
| trg_ordini_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id')` |
| trg_ordini_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id')` |
| trg_ordini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_normalize()` |
| trg_ordini_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_normalize()` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |
| trg_ordini_z90_sync_canali_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |
| trg_ordini_z90_sync_canali_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |

---
{% include-markdown "signature-core.md" %}
