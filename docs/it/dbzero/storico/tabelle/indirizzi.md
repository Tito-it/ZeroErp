# Tabella `indirizzi`

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