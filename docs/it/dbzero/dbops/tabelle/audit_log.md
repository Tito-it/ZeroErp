# Tabella `audit_log`

## Campi principali
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

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 18506_19971_1_not_null |  |
| CHECK | 18506_19971_2_not_null |  |
| CHECK | 18506_19971_3_not_null |  |
| CHECK | 18506_19971_4_not_null |  |
| CHECK | 18506_19971_6_not_null |  |
| CHECK | 18506_19971_9_not_null |  |
| PRIMARY KEY | pk_audit_log | id |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_audit_log | `CREATE UNIQUE INDEX pk_audit_log ON dbops.audit_log USING btree (id)` |