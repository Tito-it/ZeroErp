{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali.md" %}
# 📚 Tabella `offerte_commerciali`

> 📝 **Descrizione**
>
> Testata offerta commerciale: predecessore tracciato del contratto (offerta-&gt;contratto = condizioni quadro). Un'offerta propone al cliente condizioni quadro per una utility specifica (billing_account + istanza_utility), con listino di riferimento, variazione globale e offerte_commerciali_eccezioni per eccezioni puntuali. Stati: BOZZA (editabile) -&gt; EMESSA -&gt; ACCETTATA (push a contratto DRAFT) oppure RIFIUTATA. SUPERATA: terminale tecnico impostato dal trigger revisione quando viene creata una revisione successiva (fn_crea_revisione_offerta, Step 7). La versione listino viene fissata (congelata) al momento dell'emissione (§5.3). La numerazione OFC-* e' generata da config.sistema_codici (Step 5). La scadenza (validita_al) e' un avviso non bloccante (§5.6). Push idempotente tramite contratti.offerta_id UNIQUE (pattern A §6.9.3). rev 2026-05-24.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| codice | text | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| listino_id | bigint | NO |  |
| listino_versione_id | bigint | YES |  |
| valore_variazione_globale | numeric(10,4) | YES | 0 |
| tipo_variazione_globale | character varying(16) | YES |  |
| validita_dal | date | NO |  |
| validita_al | date | YES |  |
| stato_doc_offerta_id | bigint | NO |  |
| revisione_numero | integer | NO | 1 |
| revisione_padre_id | bigint | YES |  |
| data_emissione | timestamp with time zone | YES |  |
| data_accettazione | timestamp with time zone | YES |  |
| data_rifiuto | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| motivazione_rifiuto | text | YES |  |
| data_annullamento | timestamp with time zone | YES |  |
| valuta_id | integer | YES |  |
| revisione_radice_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_offerte_commerciali_valore_variazione_globale_finito |  |
| CHECK | chk_offerte_revisione_numero |  |
| CHECK | chk_offerte_tipo_variazione_globale |  |
| CHECK | chk_offerte_validita_date |  |
| CHECK | chk_offerte_variazione_globale_coerenza |  |
| FOREIGN KEY | fk_offerte_commerciali_ba_coppia | billing_account_id, istanza_utility_id, utility_id |
| FOREIGN KEY | fk_offerte_commerciali_billing_account | billing_account_id |
| FOREIGN KEY | fk_offerte_commerciali_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_offerte_commerciali_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_offerte_commerciali_listino | listino_id |
| FOREIGN KEY | fk_offerte_commerciali_listino_versione | listino_versione_id |
| FOREIGN KEY | fk_offerte_commerciali_revisione_padre | revisione_padre_id |
| FOREIGN KEY | fk_offerte_commerciali_revisione_radice | revisione_radice_id |
| FOREIGN KEY | fk_offerte_commerciali_stato_doc | stato_doc_offerta_id |
| FOREIGN KEY | fk_offerte_commerciali_utility | utility_id |
| FOREIGN KEY | fk_offerte_commerciali_valuta | valuta_id |
| PRIMARY KEY | pk_offerte_commerciali | id |
| UNIQUE | uq_offerte_commerciali_codice | codice |
| UNIQUE | uq_offerte_commerciali_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_offerte_commerciali_billing_account | `CREATE INDEX ix_offerte_commerciali_billing_account ON vendite.offerte_commerciali USING btree (billing_account_id)` |
| ix_offerte_commerciali_istanza_utility | `CREATE INDEX ix_offerte_commerciali_istanza_utility ON vendite.offerte_commerciali USING btree (istanza_utility_id)` |
| ix_offerte_commerciali_listino_versione | `CREATE INDEX ix_offerte_commerciali_listino_versione ON vendite.offerte_commerciali USING btree (listino_versione_id) WHERE (listino_versione_id IS NOT NULL)` |
| ix_offerte_commerciali_revisione_padre | `CREATE INDEX ix_offerte_commerciali_revisione_padre ON vendite.offerte_commerciali USING btree (revisione_padre_id) WHERE (revisione_padre_id IS NOT NULL)` |
| ix_offerte_commerciali_revisione_radice_id | `CREATE INDEX ix_offerte_commerciali_revisione_radice_id ON vendite.offerte_commerciali USING btree (revisione_radice_id)` |
| ix_offerte_commerciali_stato_doc | `CREATE INDEX ix_offerte_commerciali_stato_doc ON vendite.offerte_commerciali USING btree (stato_doc_offerta_id)` |
| ix_offerte_commerciali_uid_text | `CREATE INDEX ix_offerte_commerciali_uid_text ON vendite.offerte_commerciali USING btree (((uid)::text))` |
| pk_offerte_commerciali | `CREATE UNIQUE INDEX pk_offerte_commerciali ON vendite.offerte_commerciali USING btree (id)` |
| uq_offerte_commerciali_codice | `CREATE UNIQUE INDEX uq_offerte_commerciali_codice ON vendite.offerte_commerciali USING btree (codice)` |
| uq_offerte_commerciali_uid | `CREATE UNIQUE INDEX uq_offerte_commerciali_uid ON vendite.offerte_commerciali USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_offerte_commerciali_a05_lock_fuori_bozza_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'BOZZA', 'valuta_id', 'E_DOC_IDENTITA_FUORI_BOZZA', '', 'billing_account_id', 'E_DOC_CLIENTE_FUORI_BOZZA', '', 'istanza_utility_id', 'E_DOC_CLIENTE_FUORI_BOZZA', '', 'utility_id', 'E_DOC_UTILITY_IMMUTABILE', '-', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_IMMUTABILE', '-', 'listino_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'listino_versione_id', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'tipo_variazione_globale', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'valore_variazione_globale', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'validita_dal', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'validita_al', 'E_DOC_CONDIZIONI_FUORI_BOZZA', '', 'meta', 'E_DOC_CHIUSO', 'EMESSA,ACCETTATA', 'motivazione_rifiuto', 'E_DOC_CHIUSO', 'EMESSA,ACCETTATA')` |
| trg_offerte_commerciali_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_offerta_id', 'config.stati_doc_offerte')` |
| trg_offerte_commerciali_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_offerte_commerciali_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_offerte_commerciali_a10_default_revisione_radice_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_default_revisione_radice()` |
| trg_offerte_commerciali_a10_default_valuta_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_default_valuta()` |
| trg_offerte_commerciali_a10_emittenti_fiscali_require_at_7d73a6 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_offerte_commerciali_a10_emittenti_fiscali_require_at_7d73a6 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_offerte_commerciali_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_gen_codice()` |
| trg_offerte_commerciali_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_gen_codice()` |
| trg_offerte_commerciali_a10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Offerta', 'codice', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_offerte_commerciali_a10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Offerta', 'codice', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE')` |
| trg_offerte_commerciali_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_offerte_commerciali_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_offerte_commerciali_a10_guard_listino_con_righe_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_listino_con_righe('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_a10_guard_listino_documento_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_listino_documento('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_a10_guard_listino_documento_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_listino_documento('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()` |
| trg_offerte_commerciali_a10_listini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_offerte_commerciali_a10_listini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_offerte_commerciali_a10_listini_versioni_require_att_ca91fb | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_offerte_commerciali_a10_listini_versioni_require_att_ca91fb | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_offerte_commerciali_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE', 'revisione_padre_id', 'E_OFFERTA_REVISIONE_CATENA_IMMUTABILE', 'revisione_radice_id', 'E_OFFERTA_REVISIONE_CATENA_IMMUTABILE')` |
| trg_offerte_commerciali_a10_stati_doc_offerte_require_at_3731e5 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_offerte', 'attivo', 'stato_doc_offerta_id', 'id')` |
| trg_offerte_commerciali_a10_stati_doc_offerte_require_at_3731e5 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_offerte', 'attivo', 'stato_doc_offerta_id', 'id')` |
| trg_offerte_commerciali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_offerte_commerciali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_offerte_commerciali_m10_guard_annullo_con_legami_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_annullo_con_legami('OFFERTA_COMMERCIALE', 'stato_doc_offerta_id', 'config.stati_doc_offerte')` |
| trg_offerte_commerciali_m50_fornitura_segue_cliente_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_fornitura_segue_cliente('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_m50_indirizzi_seguono_cliente_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_seguono_cliente('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_z90_revisione_ins | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_revisione()` |
| trg_offerte_commerciali_z90_rientro_padre_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_offerte_commerciali_rientro_padre()` |

---
{% include-markdown "signature-core.md" %}
