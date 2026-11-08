{% include-markdown "it/dbzero/vendite/manual/commesse.md" %}
# 📚 Tabella `commesse`

> 📝 **Descrizione**
>
> Testata commessa (REALE/AUTO) con stato lifecycle e policy fatturazione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(64) | NO |  |
| tipo_commessa | character varying(16) | NO | 'AUTO'::character varying |
| policy_fatturazione | character varying(24) | NO | 'DA_DOCUMENTO'::character varying |
| fatturazione_immediata | boolean | NO | false |
| priorita_operativa | character varying(16) | NO | 'NORMALE'::character varying |
| billing_account_id | bigint | NO |  |
| utility_id | integer | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| competenza_dal | date | YES |  |
| competenza_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| stato_commessa_id | bigint | NO |  |
| termine_pagamento_id | bigint | YES |  |
| modalita_pagamento_id | integer | YES |  |
| registro_id | bigint | YES |  |
| anno | smallint | YES |  |
| descrizione | character varying(255) | YES |  |
| data_apertura | date | NO | script.fn_data_operativa() |
| responsabile_risorsa_umana_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_commesse_competenza_range |  |
| CHECK | chk_commesse_policy |  |
| CHECK | chk_commesse_priorita |  |
| CHECK | chk_commesse_tipo |  |
| FOREIGN KEY | fk_commesse_billing_account | billing_account_id |
| FOREIGN KEY | fk_commesse_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_commesse_modalita_pagamento | modalita_pagamento_id |
| FOREIGN KEY | fk_commesse_registro | registro_id |
| FOREIGN KEY | fk_commesse_risorse_umane | responsabile_risorsa_umana_id |
| FOREIGN KEY | fk_commesse_stato_commessa | stato_commessa_id |
| FOREIGN KEY | fk_commesse_termine_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_commesse_utility | utility_id |
| PRIMARY KEY | pk_commesse | id |
| UNIQUE | uq_commesse_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_ba_utility | `CREATE INDEX ix_commesse_ba_utility ON vendite.commesse USING btree (billing_account_id, utility_id)` |
| ix_commesse_registro_anno | `CREATE INDEX ix_commesse_registro_anno ON vendite.commesse USING btree (registro_id, anno)` |
| ix_commesse_stato_commessa_id | `CREATE INDEX ix_commesse_stato_commessa_id ON vendite.commesse USING btree (stato_commessa_id)` |
| pk_commesse | `CREATE UNIQUE INDEX pk_commesse ON vendite.commesse USING btree (id)` |
| uq_commesse_codice | `CREATE UNIQUE INDEX uq_commesse_codice ON vendite.commesse USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_commessa_id', 'vendite.stati_commessa')` |
| trg_commesse_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_commesse_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_commesse_default_emittente()` |
| trg_commesse_a10_guard_delete_solo_bozza_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_delete_solo_bozza()` |
| trg_commesse_a10_guard_emittente_ba_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Commessa', 'codice', 'emittente_soggetto_ruolo_id', 'E_COMMESSA_EMITTENTE_BA_INCOERENTE')` |
| trg_commesse_a10_guard_emittente_ba_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba('Commessa', 'codice', 'emittente_soggetto_ruolo_id', 'E_COMMESSA_EMITTENTE_BA_INCOERENTE')` |
| trg_commesse_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_guard_transizione()` |
| trg_commesse_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_commesse_a10_registri_fatturazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_commesse_a10_risorse_umane_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'responsabile_risorsa_umana_id', 'id')` |
| trg_commesse_a10_risorse_umane_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'responsabile_risorsa_umana_id', 'id')` |
| trg_commesse_a10_stati_commessa_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'stati_commessa', 'attivo', 'stato_commessa_id', 'id')` |
| trg_commesse_a10_stati_commessa_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'stati_commessa', 'attivo', 'stato_commessa_id', 'id')` |
| trg_commesse_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_commesse_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_commesse_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_commesse_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_commesse_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_m10_guard_annullo_con_legami_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_guard_annullo_con_legami('COMMESSA', 'stato_commessa_id', 'vendite.stati_commessa')` |
| trg_commesse_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_id')` |
| trg_commesse_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_id')` |
| trg_vendite_commesse_a10_guard_chiave_immutabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_guard_chiave_immutabile()` |
| trg_vendite_commesse_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
