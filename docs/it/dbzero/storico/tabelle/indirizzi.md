# Tabella `indirizzi`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.indirizzi_id_seq'::regclass) |
| soggetto_ruolo_id | integer | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| indirizzi_dettaglio_id | integer | YES |  |
| indirizzo_libero | text | YES |  |
| stato_id | integer | YES |  |
| valid_from | timestamp with time zone | NO | CURRENT_DATE |
| valid_to | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| comune_id | integer | YES |  |
| codice_postale_id | integer | YES |  |
| administrative_area | character varying | YES |  |
| locality | character varying | YES |  |
| sublocality | character varying | YES |  |
| postal_box | character varying | YES |  |
| geoloc | USER-DEFINED | YES |  |
| indirizzi_id | integer | YES |  |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_codici_postali_config | codice_postale_id, codice_postale_id |
| FOREIGN KEY | fk_comuni_config | comune_id, comune_id, comune_id |
| FOREIGN KEY | fk_indirizzi_anagrafiche | indirizzi_id |
| FOREIGN KEY | fk_indirizzi_dettaglio_anagrafiche | indirizzi_dettaglio_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id |
| FOREIGN KEY | fk_stati_config | stato_id |
| FOREIGN KEY | fk_tipi_indirizzi_config | tipo_indirizzo_id |
| PRIMARY KEY | pk_indirizzi | id |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_storico_indirizzi_periodo | `CREATE INDEX ix_storico_indirizzi_periodo ON storico.indirizzi USING btree (valid_from, valid_to)` |
| ix_storico_indirizzi_soggetto_ruolo | `CREATE INDEX ix_storico_indirizzi_soggetto_ruolo ON storico.indirizzi USING btree (soggetto_ruolo_id)` |
| ix_storico_indirizzi_tipo | `CREATE INDEX ix_storico_indirizzi_tipo ON storico.indirizzi USING btree (tipo_indirizzo_id)` |
| pk_indirizzi | `CREATE UNIQUE INDEX pk_indirizzi ON storico.indirizzi USING btree (id)` |