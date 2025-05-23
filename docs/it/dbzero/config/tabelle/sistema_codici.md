# Tabella `sistema_codici`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.sistema_codici_id_seq'::regclass) |
| codice_tipo | text | NO |  |
| descrizione | text | YES |  |
| prefisso | text | NO | ''::text |
| separatore | text | YES | ''::text |
| lunghezza_numero | integer | NO | 6 |
| usa_sequenza | boolean | YES | true |
| nome_sequenza | text | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| user_insert | text | YES | CURRENT_USER |
| data_update | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| user_update | text | YES | CURRENT_USER |