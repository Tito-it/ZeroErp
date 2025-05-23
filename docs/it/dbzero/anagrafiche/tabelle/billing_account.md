# Tabella `billing_account`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.billing_account_id_seq'::regclass) |
| istanza_id | integer | NO |  |
| soggetto_ruolo_id | integer | NO |  |
| utility_id | integer | NO |  |
| parent_account_id | integer | YES |  |
| account_code | character varying | NO |  |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | CURRENT_USER |