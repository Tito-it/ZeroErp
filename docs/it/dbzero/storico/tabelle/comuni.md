# Tabella `comuni`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.comuni_id_seq'::regclass) |
| descrizione | text | YES |  |
| extra_country | jsonb | YES |  |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| stato | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| comune_id | integer | YES |  |