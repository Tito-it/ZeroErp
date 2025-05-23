# Tabella `stati`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.stati_id_seq'::regclass) |
| sigla_stato | character varying | YES |  |
| descrizione | character varying | NO |  |
| codice_iso2 | character | YES |  |
| codice_iso3 | character | YES |  |
| codice_telefonico | character varying | YES |  |
| continente | character varying | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |