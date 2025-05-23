# Tabella `soggetti`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | gen_random_uuid() |
| codice | text | YES |  |
| ragione_sociale | text | YES |  |
| cognome | text | YES |  |
| nome | text | YES |  |
| tipo_soggetto | character | NO | 'F'::bpchar |
| sesso | character | YES | 'M'::bpchar |
| stato_id | integer | NO |  |
| partita_iva | text | YES |  |
| piva_gruppo_acquisto | text | YES |  |
| codice_fiscale | text | YES |  |
| data_nascita | date | YES |  |
| comune_id | integer | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |
| contatto_ruolo_id | integer | YES |  |
| identificativo_old | character varying | YES |  |
| id_fiscale_univoco_cf_piva | text | YES |  |
| ragione_sociale_completa | text | YES |  |
| default_contatto_id | integer | NO |  |