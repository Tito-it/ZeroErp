# 📚 Tabella `scope_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.scope_policy_id_seq'::regclass) |
| scope_policy_id | integer | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_scope_policy | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_scope_policy_scope_policy_id_fk | `CREATE INDEX ix_scope_policy_scope_policy_id_fk ON storico.scope_policy USING btree (scope_policy_id)` |
| pk_storico_scope_policy | `CREATE UNIQUE INDEX pk_storico_scope_policy ON storico.scope_policy USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
