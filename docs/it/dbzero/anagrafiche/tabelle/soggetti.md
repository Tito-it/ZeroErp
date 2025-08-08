{% include-markdown "it/dbzero/anagrafiche/manual/soggetti.md" %}
# 📚 Tabella `soggetti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | gen_random_uuid() |
| codice_soggetto | text | YES |  |
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
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |
| titolo_cortesia_id | integer | YES |  |
| identificativo_old | character varying | YES |  |
| ragione_sociale_completa | text | YES |  |
| default_contatto_id | integer | YES |  |
| tipo_soggetto_dettaglio_id | bigint | YES |  |
| id_fiscale_univoco_cf_piva | text | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetto_soggetto_sesso |  |
| FOREIGN KEY | fk_comuni_config | comune_id, comune_id |
| FOREIGN KEY | fk_contatti_anagrafiche | default_contatto_id |
| FOREIGN KEY | fk_soggetti_tipo_soggetto_dettaglio | tipo_soggetto_dettaglio_id |
| FOREIGN KEY | fk_stati_config | stato_id, stato_id |
| FOREIGN KEY | fk_titoli_cortesia_config | titolo_cortesia_id, titolo_cortesia_id |
| PRIMARY KEY | pk_soggetto | id |
| UNIQUE | uq_soggetto_idstato_id_fiscale_univoco | stato_id, id_fiscale_univoco_cf_piva |
| UNIQUE | uq_soggetto_soggetto_codice | codice_soggetto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_soggetti_ragione_sociale_completa | `CREATE INDEX ix_anagrafiche_soggetti_ragione_sociale_completa ON anagrafiche.soggetti USING btree (ragione_sociale_completa)` |
| ix_soggetti_comune_id | `CREATE INDEX ix_soggetti_comune_id ON anagrafiche.soggetti USING btree (comune_id)` |
| ix_soggetti_default_contatto_id | `CREATE INDEX ix_soggetti_default_contatto_id ON anagrafiche.soggetti USING btree (default_contatto_id)` |
| ix_soggetti_stato_id | `CREATE INDEX ix_soggetti_stato_id ON anagrafiche.soggetti USING btree (stato_id)` |
| ix_soggetti_tipo_soggetto_dettaglio_id | `CREATE INDEX ix_soggetti_tipo_soggetto_dettaglio_id ON anagrafiche.soggetti USING btree (tipo_soggetto_dettaglio_id)` |
| ix_soggetti_titolo_cortesia_id | `CREATE INDEX ix_soggetti_titolo_cortesia_id ON anagrafiche.soggetti USING btree (titolo_cortesia_id)` |
| pk_soggetto | `CREATE UNIQUE INDEX pk_soggetto ON anagrafiche.soggetti USING btree (id)` |
| uq_soggetto_idstato_id_fiscale_univoco | `CREATE UNIQUE INDEX uq_soggetto_idstato_id_fiscale_univoco ON anagrafiche.soggetti USING btree (stato_id, id_fiscale_univoco_cf_piva)` |
| uq_soggetto_soggetto_codice | `CREATE UNIQUE INDEX uq_soggetto_soggetto_codice ON anagrafiche.soggetti USING btree (codice_soggetto)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_ins_upd_check_soggetto_contatti | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()` |
| trg_soggetti_ins_upd_check_soggetto_contatti | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()` |
| trg_soggetti_ins_upd_clean_fields | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_clean_fields()` |
| trg_soggetti_ins_upd_clean_fields | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_clean_fields()` |
| trg_soggetti_ins_upd_dispatch_valida_cf_piva | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()` |
| trg_soggetti_ins_upd_dispatch_valida_cf_piva | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()` |
| trg_soggetti_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_upd_protect_codice_soggetto | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_upd_protect_codice_soggetto()` |
| trg_upd_soggetti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_soggetti_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('soggetto_id')` |
| trg_z90_soggetti_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('soggetto_id')` |
---
{% include-markdown "signature-core.md" %}
