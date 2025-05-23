# Tabella `conti_contabili`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.conti_contabili_id_seq'::regclass) |
| codice_conto | character varying | NO |  |
| descrizione | character varying | NO |  |
| tipo_conto | character | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |