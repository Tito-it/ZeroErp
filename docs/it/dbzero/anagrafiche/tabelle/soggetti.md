{% include-markdown "it/dbzero/anagrafiche/manual/soggetti.md" %}
# 📚 Tabella `soggetti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | gen_random_uuid() |
| codice | text | YES |  |
| ragione_sociale | text | YES |  |
| cognome | text | YES |  |
| nome | text | YES |  |
| sesso | character | YES | 'M'::bpchar |
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
| default_contatto_id | integer | YES |  |
| tipo_soggetto_dettaglio_id | bigint | YES |  |
| id_fiscale_univoco_cf_piva | text | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| attivo | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_comuni_config | comune_id, comune_id |
| FOREIGN KEY | fk_contatti_anagrafiche | default_contatto_id |
| FOREIGN KEY | fk_soggetti_tipo_soggetto_dettaglio | tipo_soggetto_dettaglio_id |
| FOREIGN KEY | fk_stati_config | stato_id, stato_id |
| FOREIGN KEY | fk_titoli_cortesia_config | titolo_cortesia_id, titolo_cortesia_id |
| PRIMARY KEY | pk_soggetto | id |
| UNIQUE | uq_soggetto_codice | codice |
| UNIQUE | uq_soggetto_idstato_id_fiscale_univoco | stato_id, id_fiscale_univoco_cf_piva |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_soggetti_comune_id | `CREATE INDEX ix_anagrafiche_soggetti_comune_id ON anagrafiche.soggetti USING btree (comune_id)` |
| ix_anagrafiche_soggetti_contatto_ruolo_id | `CREATE INDEX ix_anagrafiche_soggetti_contatto_ruolo_id ON anagrafiche.soggetti USING btree (titolo_cortesia_id)` |
| ix_anagrafiche_soggetti_ragione_sociale_completa | `CREATE INDEX ix_anagrafiche_soggetti_ragione_sociale_completa ON anagrafiche.soggetti USING btree (ragione_sociale_completa)` |
| ix_anagrafiche_soggetti_stato_id | `CREATE INDEX ix_anagrafiche_soggetti_stato_id ON anagrafiche.soggetti USING btree (stato_id)` |
| pk_soggetto | `CREATE UNIQUE INDEX pk_soggetto ON anagrafiche.soggetti USING btree (id)` |
| uq_soggetto_codice | `CREATE UNIQUE INDEX uq_soggetto_codice ON anagrafiche.soggetti USING btree (codice)` |
| uq_soggetto_idstato_id_fiscale_univoco | `CREATE UNIQUE INDEX uq_soggetto_idstato_id_fiscale_univoco ON anagrafiche.soggetti USING btree (stato_id, id_fiscale_univoco_cf_piva)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_ins_upd_check_soggetto_contatti | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()` |
| trg_soggetti_ins_upd_check_soggetto_contatti | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()` |
| trg_soggetti_ins_upd_clean_fields | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_clean_fields()` |
| trg_soggetti_ins_upd_clean_fields | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_clean_fields()` |
| trg_soggetti_ins_upd_tx_id_managed | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ins_upd_tx_id_managed | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ins_upd_valida_cf_piva_dispatch | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()` |
| trg_soggetti_ins_upd_valida_cf_piva_dispatch | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()` |
| trg_soggetti_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_soggetti_upd_protect_codice_soggetto | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_upd_protect_codice_soggetto()` |
| trg_soggetti_z90_upd_dlt_storico_generic | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('soggetto_id')` |
| trg_soggetti_z90_upd_dlt_storico_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('soggetto_id')` |

---
{% include-markdown "signature-core.md" %}
