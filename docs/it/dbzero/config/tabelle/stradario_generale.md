# Tabella `stradario_generale`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.stradario_generale_id_seq'::regclass) |
| toponomastica_id | integer | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |