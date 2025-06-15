{% include-markdown "it/dbzero/dbops/manual/audit_log.md" %}
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
| tx_id | uuid | NO | (md5((txid_current())::text))::uuid |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_audit_log | id |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_audit_log | `CREATE UNIQUE INDEX pk_audit_log ON dbops.audit_log USING btree (id)` |