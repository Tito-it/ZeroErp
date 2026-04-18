{% include-markdown "it/dbzero/config/manual/identita_scope_bindings.md" %}
# 📚 Tabella `identita_scope_bindings`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| identita_digitale_id | bigint | NO |  |
| scope_policy_id | integer | NO |  |
| parametri | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_identita_scope_bindings_identita | identita_digitale_id |
| FOREIGN KEY | fk_identita_scope_bindings_policy | scope_policy_id |
| PRIMARY KEY | pk_identita_scope_bindings | id |
| UNIQUE | uq_identita_scope_bindings_identita_policy | identita_digitale_id, scope_policy_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_identita_scope_bindings | `CREATE UNIQUE INDEX pk_identita_scope_bindings ON config.identita_scope_bindings USING btree (id)` |
| uq_identita_scope_bindings_identita_policy | `CREATE UNIQUE INDEX uq_identita_scope_bindings_identita_policy ON config.identita_scope_bindings USING btree (identita_digitale_id, scope_policy_id)` |

---
{% include-markdown "signature-core.md" %}
