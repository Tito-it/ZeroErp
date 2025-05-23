# Tabella `stradario`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.stradario_id_seq'::regclass) |
| via_id | integer | NO |  |
| comune_id | integer | NO |  |
| codice_postale_id | integer | YES |  |
| descrizione_via | text | YES |  |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| stato | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| stradario_id | integer | YES |  |