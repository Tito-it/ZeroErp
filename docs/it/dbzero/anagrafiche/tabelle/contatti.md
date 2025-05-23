# Tabella `contatti`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.contatti_id_seq'::regclass) |
| tipo_contatto_id | integer | NO |  |
| soggetto_id | uuid | NO |  |
| soggetto_ruolo_id | integer | NO |  |
| utility_id | integer | NO |  |
| nominativo | character varying | NO |  |
| email | character varying | YES |  |
| telefono | character varying | YES |  |
| cellulare | character varying | YES |  |
| pec | character varying | YES |  |
| note | text | YES |  |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| is_default | boolean | NO | false |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |