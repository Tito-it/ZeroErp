# Tabella `clienti`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.clienti_id_seq'::regclass) |
| soggetto_ruolo_id | integer | NO |  |
| istanza_id | integer | YES |  |
| tipo_gg_scadenza_ft | character | NO | 'N'::bpchar |
| nr_giorni_scadenza | integer | NO | 0 |
| modalita_pagamento_id | integer | YES |  |
| cliente_pa | character | NO | 'N'::bpchar |
| codice_cig | character varying | YES |  |
| codice_cup | character varying | YES |  |
| cod_commessa | character varying | YES |  |
| split_payment | character | NO | 'N'::bpchar |
| cd_cliente_importato | character varying | YES |  |
| stato_cliente_id | integer | NO |  |
| iva_id | integer | NO |  |
| servizio_da_fatturare | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | CURRENT_USER |
| utility_id | integer | YES |  |