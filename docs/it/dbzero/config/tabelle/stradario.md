# Tabella `stradario`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.stradario_id_seq'::regclass) |
| comune_id | integer | NO |  |
| via_id | integer | NO |  |
| geoloc | USER-DEFINED | YES |  |
| extra_info | jsonb | YES |  |
| data_insert | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| data_update | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| user_update | character varying | YES | CURRENT_USER |
| codice_postale_id | integer | NO |  |
| storicizza | boolean | NO | false |