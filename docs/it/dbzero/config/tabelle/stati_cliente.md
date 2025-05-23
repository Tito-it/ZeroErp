# Tabella `stati_cliente`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.stati_cliente_id_seq'::regclass) |
| cod_int_stato_cliente | character | NO |  |
| desc_stato_cliente | character varying | NO | ''::character varying |
| desc_breve_stato | character | NO |  |
| check_lettura | character | NO | 'S'::bpchar |
| abilita_fattura | character | NO | 'S'::bpchar |
| stato_cliente | character | NO | 'IS'::bpchar |
| stato_cliente_ia | character | NO | 'I'::bpchar |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |