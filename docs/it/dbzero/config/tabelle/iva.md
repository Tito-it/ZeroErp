# Tabella `iva`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.iva_id_seq'::regclass) |
| codice_iva | character | NO |  |
| desc_iva | character varying | NO |  |
| desc_breve_iva | character varying | NO |  |
| aliquota_iva | numeric | NO | 0 |
| assoggettamento_iva | character | NO | ''::bpchar |
| natura_iva_id | integer | YES |  |
| conto_iva_acquisti_id | integer | YES |  |
| conto_iva_vendita_id | integer | YES |  |
| id_iva_split | integer | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |