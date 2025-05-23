# Tabella `istanze_utilities`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.istanze_utilities_id_seq'::regclass) |
| soggetto_ruolo_id | integer | NO |  |
| fittizia | boolean | NO | false |
| codice_istanza | character varying | NO |  |
| proprietario_inquilino | character | NO | 'I'::bpchar |
| destinazione_immobile | character | YES |  |
| num_concessione | character varying | YES |  |
| data_concessione | date | YES |  |
| sezione_catastale | character | YES |  |
| foglio_catastale | character | YES |  |
| particella | character | YES |  |
| subalterno | character | YES |  |
| anno_protocollo | integer | YES |  |
| superficie | integer | YES |  |
| immobile_rurale | boolean | NO | false |
| tipo_accatastamento | character | YES |  |
| categoria_catastale | character varying | YES |  |
| classe_catastale | character varying | YES |  |
| rendita_catastale | numeric | YES |  |
| consistenza | integer | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| account_code | character varying | YES |  |