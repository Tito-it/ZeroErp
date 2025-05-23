# Tabella `audit_log`

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('dbops.audit_log_id_seq'::regclass) |
| function_name | text | NO |  |
| executed_by | text | NO | CURRENT_USER |
| executed_at | timestamp with time zone | NO | now() |
| params | jsonb | YES |  |
| status | text | NO |  |
| message | text | YES |  |
| duration_ms | integer | YES |  |
| tx_id | uuid | NO | gen_random_uuid() |