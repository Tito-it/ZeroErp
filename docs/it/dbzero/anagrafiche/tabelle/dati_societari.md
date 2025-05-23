# Tabella `dati_societari`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id_dati_societari | bigint | NO | nextval('anagrafiche.dati_societari_id_seq'::regclass) |
| soggetto_id | uuid | NO |  |
| forma_giuridica | text | NO |  |
| capitale_sociale | numeric | NO |  |
| id_prov_iscri_rea | integer | NO |  |
| iscrizione_rea | character varying | NO |  |
| socio_unico | USER-DEFINED | NO | 'SU'::anagrafiche.socio_unico_enum |
| liquidazione | USER-DEFINED | NO | 'LN'::anagrafiche.liquidazione_enum |
| destinatario_fe | character | NO |  |
| pec_fatturazione | character varying | YES |  |
| codice_sdi | character varying | YES |  |
| data_costituzione | date | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |