# Tabella `tipi_ruoli`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.tipi_ruoli_id_seq'::regclass) |
| cod_ruolo | character varying | NO |  |
| descrizione | character varying | NO |  |
| cd_int_ruolo | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |