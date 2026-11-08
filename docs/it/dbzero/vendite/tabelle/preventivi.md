{% include-markdown "it/dbzero/vendite/manual/preventivi.md" %}
# 📚 Tabella `preventivi`

> 📝 **Descrizione**
>
> Preventivi/offerte con revisioni; una sola revisione attiva per numero

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| numero | character varying(30) | NO |  |
| rev | integer | NO | 0 |
| billing_account_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| validita_dal | date | YES |  |
| validita_al | date | YES |  |
| totale_imponibile | numeric(15,2) | YES | 0 |
| totale_iva | numeric(15,2) | YES | 0 |
| totale_documento | numeric(15,2) | YES | 0 |
| valuta_id | integer | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| competenza_mese | date | YES |  |
| fatturazione_immediata | boolean | YES | false |
| stato_doc_preventivo_id | bigint | NO |  |
| data | date | NO | script.fn_data_operativa() |
| termine_pagamento_id | bigint | YES |  |
| uid | uuid | NO | uuidv7() |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| emittente_fiscale_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_preventivi_competenza_mese_primo |  |
| CHECK | chk_preventivi_totale_documento_finito |  |
| CHECK | chk_preventivi_totale_imponibile_finito |  |
| CHECK | chk_preventivi_totale_iva_finito |  |
| CHECK | chk_preventivi_validita |  |
| FOREIGN KEY | fk_preventivi_ba_coppia | billing_account_id, istanza_utility_id, utility_id |
| FOREIGN KEY | fk_preventivi_billing_account | billing_account_id |
| FOREIGN KEY | fk_preventivi_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_preventivi_istanza | istanza_utility_id |
| FOREIGN KEY | fk_preventivi_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_preventivi_utility | utility_id |
| FOREIGN KEY | fk_preventivi_valuta | valuta_id |
| FOREIGN KEY | fk_v_preventivi_stato_ddt | stato_doc_preventivo_id |
| PRIMARY KEY | pk_preventivi | id |
| UNIQUE | uq_preventivi_numero_rev | numero, rev |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_preventivi_emittente_fiscale_id | `CREATE INDEX ix_preventivi_emittente_fiscale_id ON vendite.preventivi USING btree (emittente_fiscale_id)` |
| ix_preventivi_uid_text | `CREATE INDEX ix_preventivi_uid_text ON vendite.preventivi USING btree (((uid)::text))` |
| pk_preventivi | `CREATE UNIQUE INDEX pk_preventivi ON vendite.preventivi USING btree (id)` |
| uq_preventivi_numero_rev | `CREATE UNIQUE INDEX uq_preventivi_numero_rev ON vendite.preventivi USING btree (numero, rev)` |
| uq_preventivi_uid | `CREATE UNIQUE INDEX uq_preventivi_uid ON vendite.preventivi USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_a05_lock_fuori_bozza_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza('PREVENTIVO', 'DRAFT', 'data', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'valuta_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'rev', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'billing_account_id', 'E_DOC_CLIENTE_FUORI_BOZZA', '', 'istanza_utility_id', 'E_DOC_CLIENTE_FUORI_BOZZA', '', 'utility_id', 'E_DOC_UTILITY_IMMUTABILE', '-', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_IMMUTABILE', '-', 'termine_pagamento_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'validita_dal', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'validita_al', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'competenza_mese', 'E_DOC_CONDIZIONI_FUORI_BOZZA', 'EMESSO,ACCETTATO', 'meta', 'E_DOC_CHIUSO', 'EMESSO,ACCETTATO')` |
| trg_preventivi_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_preventivo_id', 'config.stati_doc_preventivi')` |
| trg_preventivi_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_preventivi_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_preventivi_a10_default_valuta_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_default_valuta()` |
| trg_preventivi_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_preventivi_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_preventivi_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_gen_codice()` |
| trg_preventivi_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_gen_codice()` |
| trg_preventivi_a10_guard_annullamento_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_guard_annullamento()` |
| trg_preventivi_a10_guard_data_vs_consegne_righe_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_testata_guard_data_consegna_righe('PREVENTIVO')` |
| trg_preventivi_a10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Preventivo', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_preventivi_a10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Preventivo', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_preventivi_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_preventivi_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_preventivi_a10_guard_fatt_immediata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('PREVENTIVO')` |
| trg_preventivi_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_guard_transizione()` |
| trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_guard_utility_istanza_coerenza()` |
| trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_guard_utility_istanza_coerenza()` |
| trg_preventivi_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'E_CODICE_NON_MODIFICABILE')` |
| trg_preventivi_a10_stati_doc_preventivi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_doc_preventivo_id', 'id')` |
| trg_preventivi_a10_stati_doc_preventivi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_doc_preventivo_id', 'id')` |
| trg_preventivi_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_preventivi_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_preventivi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_preventivi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_preventivi_m10_guard_annullo_con_legami_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_annullo_con_legami('PREVENTIVO', 'stato_doc_preventivo_id', 'config.stati_doc_preventivi')` |
| trg_preventivi_m50_indirizzi_seguono_cliente_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_seguono_cliente('PREVENTIVO')` |
| trg_preventivi_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_normalize()` |
| trg_preventivi_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_normalize()` |
| trg_preventivi_z90_reconcile_proiezione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_documento_reconcile_proiezione('PREVENTIVO')` |
| trg_preventivi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('preventivi_id')` |
| trg_preventivi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('preventivi_id')` |
| trg_vendite_preventivi_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
