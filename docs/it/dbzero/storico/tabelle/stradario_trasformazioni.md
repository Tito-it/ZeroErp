# Tabella `stradario_trasformazioni`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.stradario_trasformazioni_id_seq'::regclass) |
| via_id_orig | integer | NO |  |
| via_id_nuovo | integer | NO |  |
| tipo_evento | character | NO |  |
| data_evento | date | NO |  |
| note | text | YES |  |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |