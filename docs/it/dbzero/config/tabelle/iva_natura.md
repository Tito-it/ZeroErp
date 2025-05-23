# Tabella `iva_natura`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.iva_natura_id_seq'::regclass) |
| codice_natura | character | NO |  |
| descrizione_natura | character varying | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |