# 📚 Tabella `indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.indirizzi_id_seq'::regclass) |
| soggetto_ruolo_id | integer | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| indirizzo_dettaglio_id | integer | YES |  |
| indirizzo_libero | text | YES |  |
| stato_id | integer | YES |  |
| administrative_area | character varying | YES |  |
| locality | character varying | YES |  |
| sublocality | character varying | YES |  |
| postal_box | character varying | YES |  |
| geoloc | USER-DEFINED | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| comune_id | integer | YES |  |
| codice_postale_id | integer | YES |  |
| modifica_storica | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_indirizzi_dettaglio_exclusive |  |
| CHECK | chk_indirizzi_fallback_required |  |
| FOREIGN KEY | fk_codici_postali_config | codice_postale_id |
| FOREIGN KEY | fk_comuni_config | comune_id, comune_id |
| FOREIGN KEY | fk_indirizzi_dettaglio_anagrafiche | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_config | stato_id, stato_id |
| FOREIGN KEY | fk_tipi_indirizzo_config | tipo_indirizzo_id |
| PRIMARY KEY | pr_indirizzi_pk | id |
| UNIQUE | uq_indirizzi_dettaglio_unique | indirizzo_dettaglio_id, tipo_indirizzo_id, soggetto_ruolo_id |
| UNIQUE | uq_indirizzi_libero_unique | tipo_indirizzo_id, soggetto_ruolo_id, indirizzo_libero |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_indirizzi_codice_postale_id | `CREATE INDEX ix_indirizzi_codice_postale_id ON anagrafiche.indirizzi USING btree (codice_postale_id)` |
| ix_indirizzi_comune_id | `CREATE INDEX ix_indirizzi_comune_id ON anagrafiche.indirizzi USING btree (comune_id)` |
| ix_indirizzi_geoloc_gist | `CREATE INDEX ix_indirizzi_geoloc_gist ON anagrafiche.indirizzi USING gist (geoloc)` |
| ix_indirizzi_soggetto_ruolo_id | `CREATE INDEX ix_indirizzi_soggetto_ruolo_id ON anagrafiche.indirizzi USING btree (soggetto_ruolo_id)` |
| ix_indirizzi_stato_id | `CREATE INDEX ix_indirizzi_stato_id ON anagrafiche.indirizzi USING btree (stato_id)` |
| ix_indirizzi_tipo_indirizzo_id | `CREATE INDEX ix_indirizzi_tipo_indirizzo_id ON anagrafiche.indirizzi USING btree (tipo_indirizzo_id)` |
| pr_indirizzi_pk | `CREATE UNIQUE INDEX pr_indirizzi_pk ON anagrafiche.indirizzi USING btree (id)` |
| uq_indirizzi_dettaglio_unique | `CREATE UNIQUE INDEX uq_indirizzi_dettaglio_unique ON anagrafiche.indirizzi USING btree (soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id)` |
| uq_indirizzi_libero_unique | `CREATE UNIQUE INDEX uq_indirizzi_libero_unique ON anagrafiche.indirizzi USING btree (soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_indirizzi_ins_upd_clean_fields | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_ins_upd_clean_fields()` |
| trg_indirizzi_ins_upd_clean_fields | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_ins_upd_clean_fields()` |
| trg_indirizzi_upd_dlt_storico_indirizzi | BEFORE | DELETE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_upd_dlt_storico_indirizzi()` |
| trg_indirizzi_upd_dlt_storico_indirizzi | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_upd_dlt_storico_indirizzi()` |
| trg_upd_indirizzi_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |