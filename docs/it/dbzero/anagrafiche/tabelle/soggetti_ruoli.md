# Tabella `soggetti_ruoli`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.soggetti_ruoli_id_seq'::regclass) |
| soggetto_id | uuid | NO |  |
| ruolo_id | integer | NO |  |
| extra | jsonb | YES | '{}'::jsonb |
| user_insert | character varying | NO |  |
| user_update | character varying | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |