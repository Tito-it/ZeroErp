# Tabella `indirizzi_dettaglio`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.indirizzi_dettaglio_id_seq'::regclass) |
| stradario_id | integer | NO |  |
| civico | integer | YES |  |
| estensione_civico | character varying | YES |  |
| palazzina | character varying | YES |  |
| interno | character varying | YES |  |
| piano | character varying | YES |  |
| civic_geoloc | USER-DEFINED | YES |  |
| altro | text | YES |  |
| via_norm | text | NO |  |
| civico_norm | text | NO |  |
| street_geoloc | USER-DEFINED | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| scala | character varying | YES |  |
| indirizzo_normalizzato | text | YES |  |