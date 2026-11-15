{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti.md" %}
# 📚 Tabella `fatturazione_lotti`

> 📝 **Descrizione**
>
> Lotti di fatturazione con parametri, lock uuid e stati operativi.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lock_batch_id | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| competenza_mese | date | NO |  |
| utility_id | integer | YES |  |
| billing_account_id | bigint | YES |  |
| stato_lotto | text | NO | 'IN_ESECUZIONE'::text |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| stato_doc_fiscale_id | bigint | NO |  |
| tipo_doc_fiscale_id | bigint | NO |  |
| area_geografica_id | bigint | YES |  |
| tipo_lotto | text | NO | 'MASSIVO'::text |
| stato_operativo | text | NO | 'APERTO'::text |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| riaperto_il | timestamp with time zone | YES |  |
| data_documento | date | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lotti_stato_operativo |  |
| CHECK | chk_fatturazione_lotti_tipo_lotto |  |
| FOREIGN KEY | fk_fatturazione_lotti_area_geografica | area_geografica_id |
| FOREIGN KEY | fk_fatturazione_lotti_ba | billing_account_id |
| FOREIGN KEY | fk_fatturazione_lotti_emittente_sr | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatturazione_lotti_stato_doc_fiscale | stato_doc_fiscale_id |
| FOREIGN KEY | fk_fatturazione_lotti_stato_lotto | stato_lotto |
| FOREIGN KEY | fk_fatturazione_lotti_tipo_doc_fiscale | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_fatturazione_lotti_utility | utility_id |
| PRIMARY KEY | pk_fatturazione_lotti | id |
| UNIQUE | uq_fatturazione_lotti_codice | codice |
| UNIQUE | uq_fatturazione_lotti_lock_batch_id | lock_batch_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti | `CREATE UNIQUE INDEX pk_fatturazione_lotti ON vendite.fatturazione_lotti USING btree (id)` |
| uq_fatturazione_lotti_codice | `CREATE UNIQUE INDEX uq_fatturazione_lotti_codice ON vendite.fatturazione_lotti USING btree (codice)` |
| uq_fatturazione_lotti_lock_batch_id | `CREATE UNIQUE INDEX uq_fatturazione_lotti_lock_batch_id ON vendite.fatturazione_lotti USING btree (lock_batch_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_fiscale_id', 'config.stati_doc_fiscale')` |
| trg_fatturazione_lotti_a05_stato_solo_dal_verbo_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()` |
| trg_fatturazione_lotti_a10_area_geografica_fatturazione_2ad64f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_fatturazione_lotti_a10_area_geografica_fatturazione_2ad64f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_fatturazione_lotti_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatturazione_lotti_gen_codice()` |
| trg_fatturazione_lotti_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatturazione_lotti_gen_codice()` |
| trg_fatturazione_lotti_a10_guard_completato_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatturazione_lotti_guard_completato()` |
| trg_fatturazione_lotti_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_fatturazione_lotti_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_fatturazione_lotti_a10_guard_stato_job_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato_job()` |
| trg_fatturazione_lotti_a10_guard_stato_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato()` |
| trg_fatturazione_lotti_a10_stati_doc_fiscale_require_att_f6cf27 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_a10_stati_doc_fiscale_require_att_f6cf27 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_a10_tipi_doc_fiscale_require_atti_662b04 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_a10_tipi_doc_fiscale_require_atti_662b04 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatturazione_lotti_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_fatturazione_lotti_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_fatturazione_lotti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_def_guard_stato_fatture_coerente_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_lotto_fatture_guard_stato_coerente()` |
| trg_fatturazione_lotti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_id')` |
| trg_fatturazione_lotti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_id')` |

---
{% include-markdown "signature-core.md" %}
