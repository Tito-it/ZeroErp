# Tabella `comuni`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.comuni_id_seq'::regclass) |
| descrizione | character varying | NO | ''::character varying |
| provincia_id | integer | YES |  |
| stato_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |
| storicizza | boolean | NO | false |