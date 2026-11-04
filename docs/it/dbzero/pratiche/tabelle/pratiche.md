{% include-markdown "it/dbzero/pratiche/manual/pratiche.md" %}
# 📚 Tabella `pratiche`

> 📝 **Descrizione**
>
> Pratiche operative — entita' principale del workflow.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| tipo_prestazione_id | integer | NO |  |
| soggetto_id | uuid | YES |  |
| stato_id | integer | NO |  |
| priorita_id | integer | NO |  |
| risorsa_umana_id | bigint | YES |  |
| unita_organizzativa_id | integer | YES |  |
| pratica_padre_id | bigint | YES |  |
| flusso_origine_id | bigint | YES |  |
| canale_origine_id | integer | YES |  |
| codice | text | YES |  |
| descrizione | text | YES |  |
| data_scadenza | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| soggetto_ruolo_id | bigint | YES |  |
| istanza_utility_id | bigint | YES |  |
| data_apertura | date | YES |  |
| definizione_id | integer | NO |  |
| billing_account_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_pratiche_ba_con_istanza |  |
| FOREIGN KEY | fk_pratiche_billing_account_istanza | billing_account_id, istanza_utility_id |
| FOREIGN KEY | fk_pratiche_canale_origine | canale_origine_id |
| FOREIGN KEY | fk_pratiche_definizione | definizione_id, tipo_prestazione_id |
| FOREIGN KEY | fk_pratiche_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_pratiche_flusso_origine | flusso_origine_id |
| FOREIGN KEY | fk_pratiche_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_pratiche_pratica_padre | pratica_padre_id |
| FOREIGN KEY | fk_pratiche_priorita | priorita_id |
| FOREIGN KEY | fk_pratiche_risorsa_umana | risorsa_umana_id |
| FOREIGN KEY | fk_pratiche_soggetto | soggetto_id |
| FOREIGN KEY | fk_pratiche_soggetto_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_pratiche_stato | stato_id |
| FOREIGN KEY | fk_pratiche_tipo_prestazione | tipo_prestazione_id |
| FOREIGN KEY | fk_pratiche_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | pk_pratiche_pratiche | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pratiche_billing_account_id_istanza_utility_id | `CREATE INDEX ix_pratiche_billing_account_id_istanza_utility_id ON pratiche.pratiche USING btree (billing_account_id, istanza_utility_id) WHERE (billing_account_id IS NOT NULL)` |
| ix_pratiche_emittente_fiscale_id | `CREATE INDEX ix_pratiche_emittente_fiscale_id ON pratiche.pratiche USING btree (emittente_fiscale_id)` |
| ix_pratiche_istanza_utility_id | `CREATE INDEX ix_pratiche_istanza_utility_id ON pratiche.pratiche USING btree (istanza_utility_id) WHERE (istanza_utility_id IS NOT NULL)` |
| ix_pratiche_soggetto_ruolo_id | `CREATE INDEX ix_pratiche_soggetto_ruolo_id ON pratiche.pratiche USING btree (soggetto_ruolo_id) WHERE (soggetto_ruolo_id IS NOT NULL)` |
| pk_pratiche_pratiche | `CREATE UNIQUE INDEX pk_pratiche_pratiche ON pratiche.pratiche USING btree (id)` |
| uq_pratiche_flusso_origine_tipo | `CREATE UNIQUE INDEX uq_pratiche_flusso_origine_tipo ON pratiche.pratiche USING btree (flusso_origine_id, tipo_prestazione_id) WHERE (flusso_origine_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pratiche_a10_canali_pratiche_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'canali_pratiche', 'attivo', 'canale_origine_id', 'id')` |
| trg_pratiche_a10_canali_pratiche_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'canali_pratiche', 'attivo', 'canale_origine_id', 'id')` |
| trg_pratiche_a10_default_definizione_ins | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_default_definizione()` |
| trg_pratiche_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_pratiche_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_pratiche_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_pratiche_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_gen_codice()` |
| trg_pratiche_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_gen_codice()` |
| trg_pratiche_a10_guard_chiusura_flussi_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_chiusura_flussi()` |
| trg_pratiche_a10_guard_contesto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_contesto()` |
| trg_pratiche_a10_guard_contesto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_contesto()` |
| trg_pratiche_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_pratiche_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_pratiche_a10_guard_pin_immutabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_pin_immutabile()` |
| trg_pratiche_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_transizione()` |
| trg_pratiche_a10_priorita_pratiche_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'priorita_pratiche', 'attivo', 'priorita_id', 'id')` |
| trg_pratiche_a10_priorita_pratiche_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'priorita_pratiche', 'attivo', 'priorita_id', 'id')` |
| trg_pratiche_a10_risorse_umane_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_pratiche_a10_risorse_umane_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'risorse_umane', 'attivo', 'risorsa_umana_id', 'id')` |
| trg_pratiche_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_pratiche_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_pratiche_a10_stati_pratiche_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_pratiche', 'attivo', 'stato_id', 'id')` |
| trg_pratiche_a10_stati_pratiche_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_pratiche', 'attivo', 'stato_id', 'id')` |
| trg_pratiche_a10_tipi_prestazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_pratiche_a10_tipi_prestazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_pratiche_a10_tipi_prestazione_require_non_obsoleto_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('pratiche', 'tipi_prestazione', 'obsoleto_dal', 'tipo_prestazione_id', 'id')` |
| trg_pratiche_a10_tipi_prestazione_require_non_obsoleto_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('pratiche', 'tipi_prestazione', 'obsoleto_dal', 'tipo_prestazione_id', 'id')` |
| trg_pratiche_a10_unita_organizzative_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_pratiche_a10_unita_organizzative_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_pratiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_pratiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_pratiche_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pratiche_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pratiche_m50_set_data_apertura_ins | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_set_data_apertura()` |
| trg_pratiche_m50_set_data_apertura_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_set_data_apertura()` |
| trg_pratiche_z90_giornale_assegnazione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_assegnazione()` |
| trg_pratiche_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_ins()` |
| trg_pratiche_z90_giornale_priorita_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_priorita()` |
| trg_pratiche_z90_giornale_stato_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_pratiche_giornale_stato()` |
| trg_pratiche_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('pratiche_id')` |
| trg_pratiche_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('pratiche_id')` |

---
{% include-markdown "signature-core.md" %}
