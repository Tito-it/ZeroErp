{% include-markdown "it/dbzero/anagrafiche/manual/indirizzi.md" %}
# 📚 Tabella `indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| indirizzo_dettaglio_id | bigint | YES |  |
| indirizzo_libero | text | YES |  |
| stato_id | integer | YES |  |
| administrative_area | character varying | YES |  |
| locality | character varying | YES |  |
| sublocality | character varying | YES |  |
| postal_box | character varying | YES |  |
| geoloc | USER-DEFINED | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| comune_id | integer | YES |  |
| codice_postale_id | integer | YES |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_codici_postali_config | codice_postale_id |
| FOREIGN KEY | fk_comuni_config | comune_id, comune_id |
| FOREIGN KEY | fk_indirizzi_dettaglio_anagrafiche | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_config | stato_id, stato_id |
| FOREIGN KEY | fk_tipi_indirizzo_config | tipo_indirizzo_id |
| PRIMARY KEY | pk_indirizzi | id |
| UNIQUE | uq_indirizzi_ruolo_tipo | tipo_indirizzo_id, soggetto_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_indirizzi_indirizzo_dettaglio_id | `CREATE INDEX ix_anagrafiche_indirizzi_indirizzo_dettaglio_id ON anagrafiche.indirizzi USING btree (indirizzo_dettaglio_id)` |
| ix_indirizzi_codice_postale_id | `CREATE INDEX ix_indirizzi_codice_postale_id ON anagrafiche.indirizzi USING btree (codice_postale_id)` |
| ix_indirizzi_comune_id | `CREATE INDEX ix_indirizzi_comune_id ON anagrafiche.indirizzi USING btree (comune_id)` |
| ix_indirizzi_geoloc_gist | `CREATE INDEX ix_indirizzi_geoloc_gist ON anagrafiche.indirizzi USING btree (geoloc)` |
| ix_indirizzi_soggetto_ruolo_id | `CREATE INDEX ix_indirizzi_soggetto_ruolo_id ON anagrafiche.indirizzi USING btree (soggetto_ruolo_id)` |
| ix_indirizzi_stato_id | `CREATE INDEX ix_indirizzi_stato_id ON anagrafiche.indirizzi USING btree (stato_id)` |
| ix_indirizzi_tipo_indirizzo_id | `CREATE INDEX ix_indirizzi_tipo_indirizzo_id ON anagrafiche.indirizzi USING btree (tipo_indirizzo_id)` |
| pk_indirizzi | `CREATE UNIQUE INDEX pk_indirizzi ON anagrafiche.indirizzi USING btree (id)` |
| uq_indirizzi_ruolo_tipo | `CREATE UNIQUE INDEX uq_indirizzi_ruolo_tipo ON anagrafiche.indirizzi USING btree (soggetto_ruolo_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_indirizzi_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_indirizzi_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_normalize()` |
| trg_indirizzi_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_normalize()` |
| trg_indirizzi_sync_geoloc_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc()` |
| trg_indirizzi_sync_geoloc_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc()` |
| trg_indirizzi_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_z90_storico_generic_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzo_id')` |
| trg_indirizzi_z90_storico_generic_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzo_id')` |

---
{% include-markdown "signature-core.md" %}
