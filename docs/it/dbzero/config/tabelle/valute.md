# Tabella `valute`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.valute_id_seq'::regclass) |
| cd_valuta | character | NO |  |
| iso_code | character | NO |  |
| iso_num_code | smallint | YES |  |
| descrizione_valuta | character varying | NO |  |
| simbolo | character varying | NO |  |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |