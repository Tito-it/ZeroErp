{% include-markdown "it/dbzero/anagrafiche/manual/soggetti.md" %}
# 📚 Tabella `soggetti`

> 📝 **Descrizione**
>
> Anagrafica soggetti (persone fisiche e giuridiche)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| codice | text | YES |  |
| ragione_sociale | text | YES |  |
| cognome | text | YES |  |
| nome | text | YES |  |
| sesso | character(1) | YES |  |
| stato_id | integer | NO |  |
| partita_iva | text | YES |  |
| piva_gruppo_acquisto | text | YES |  |
| codice_fiscale | text | YES |  |
| data_nascita | date | YES |  |
| comune_id | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| titolo_cortesia_id | integer | YES |  |
| identificativo_old | character varying | YES |  |
| ragione_sociale_completa | text | YES |  |
| default_contatto_id | bigint | YES |  |
| tipo_soggetto_dettaglio_id | bigint | YES |  |
| id_fiscale_univoco_cf_piva | text | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| attivo | boolean | NO | true |
| split_payment | character(1) | NO | 'N'::bpchar |
| cliente_pa | character(1) | NO | 'N'::bpchar |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetti_cliente_pa |  |
| CHECK | chk_soggetti_sesso |  |
| CHECK | chk_soggetti_split_payment |  |
| FOREIGN KEY | fk_comuni_config | comune_id |
| FOREIGN KEY | fk_contatti_anagrafiche | default_contatto_id |
| FOREIGN KEY | fk_soggetti_tipo_soggetto_dettaglio | tipo_soggetto_dettaglio_id |
| FOREIGN KEY | fk_stati_config | stato_id |
| FOREIGN KEY | fk_titoli_cortesia_config | titolo_cortesia_id |
| PRIMARY KEY | pk_soggetto | id |
| UNIQUE | uq_soggetto_codice | codice |
| UNIQUE | uq_soggetto_idstato_id_fiscale_univoco | stato_id, id_fiscale_univoco_cf_piva |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_soggetti_comune_id | `CREATE INDEX ix_anagrafiche_soggetti_comune_id ON anagrafiche.soggetti USING btree (comune_id)` |
| ix_anagrafiche_soggetti_ragione_sociale_completa | `CREATE INDEX ix_anagrafiche_soggetti_ragione_sociale_completa ON anagrafiche.soggetti USING btree (ragione_sociale_completa)` |
| ix_anagrafiche_soggetti_titolo_cortesia_id | `CREATE INDEX ix_anagrafiche_soggetti_titolo_cortesia_id ON anagrafiche.soggetti USING btree (titolo_cortesia_id)` |
| ix_soggetti_codice_trgm | `CREATE INDEX ix_soggetti_codice_trgm ON anagrafiche.soggetti USING gin (codice gin_trgm_ops)` |
| ix_soggetti_id_fiscale_univoco_trgm | `CREATE INDEX ix_soggetti_id_fiscale_univoco_trgm ON anagrafiche.soggetti USING gin (id_fiscale_univoco_cf_piva gin_trgm_ops) WITH (fastupdate='true', gin_pending_list_limit='4194304')` |
| ix_soggetti_ragione_sociale_completa_trgm | `CREATE INDEX ix_soggetti_ragione_sociale_completa_trgm ON anagrafiche.soggetti USING gin (ragione_sociale_completa gin_trgm_ops) WITH (fastupdate='true', gin_pending_list_limit='4194304')` |
| pk_soggetto | `CREATE UNIQUE INDEX pk_soggetto ON anagrafiche.soggetti USING btree (id)` |
| uq_soggetto_codice | `CREATE UNIQUE INDEX uq_soggetto_codice ON anagrafiche.soggetti USING btree (codice)` |
| uq_soggetto_idstato_id_fiscale_univoco | `CREATE UNIQUE INDEX uq_soggetto_idstato_id_fiscale_univoco ON anagrafiche.soggetti USING btree (stato_id, id_fiscale_univoco_cf_piva)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_a10_contatti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'contatti', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_dati_societari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'dati_societari', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_gen_codice()` |
| trg_soggetti_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_gen_codice()` |
| trg_soggetti_a10_guard_cf_piva_obbligatori_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori()` |
| trg_soggetti_a10_guard_cf_piva_obbligatori_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori()` |
| trg_soggetti_a10_guard_regime_pa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_regime_pa()` |
| trg_soggetti_a10_guard_regime_pa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_regime_pa()` |
| trg_soggetti_a10_guard_sesso_policy_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_sesso_policy()` |
| trg_soggetti_a10_guard_sesso_policy_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_sesso_policy()` |
| trg_soggetti_a10_guard_titoli_iva_ammessi_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_titoli_iva_ammessi()` |
| trg_soggetti_a10_indirizzi_soggetti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'indirizzi_soggetti', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_istanze_utilities_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'istanze_utilities', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE')` |
| trg_soggetti_a10_pratiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'pratiche', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_risorse_umane_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'risorse_umane', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_soggetti_conti_bancari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_conti_bancari', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_soggetti_ruoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_ruoli', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a10_soggetti_titoli_iva_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva', 'soggetto_id', 'id', 'attivo')` |
| trg_soggetti_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_soggetti_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_soggetti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_def_guard_dati_societari_required_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_dati_societari_required()` |
| trg_soggetti_def_guard_dati_societari_required_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_dati_societari_required()` |
| trg_soggetti_def_guard_forma_giuridica_natura_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_forma_giuridica_natura()` |
| trg_soggetti_def_guard_indirizzi_required_aft_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_indirizzi_required()` |
| trg_soggetti_def_guard_indirizzi_required_aft_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_indirizzi_required()` |
| trg_soggetti_def_guard_soggetto_contatti_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_soggetto_contatti()` |
| trg_soggetti_def_guard_soggetto_contatti_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_guard_soggetto_contatti()` |
| trg_soggetti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_normalize()` |
| trg_soggetti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_normalize()` |
| trg_soggetti_valida_cf_piva_dispatch_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()` |
| trg_soggetti_valida_cf_piva_dispatch_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()` |
| trg_soggetti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetto_id')` |
| trg_soggetti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetto_id')` |

---
{% include-markdown "signature-core.md" %}
