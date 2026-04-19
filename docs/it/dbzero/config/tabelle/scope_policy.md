{% include-markdown "it/dbzero/config/manual/scope_policy.md" %}
# 📚 Tabella `scope_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | text | NO |  |
| funzione_db | character varying | NO |  |
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
| PRIMARY KEY | pk_scope_policy | id |
| UNIQUE | uq_scope_policy_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_scope_policy | `CREATE UNIQUE INDEX pk_scope_policy ON config.scope_policy USING btree (id)` |
| uq_scope_policy_codice | `CREATE UNIQUE INDEX uq_scope_policy_codice ON config.scope_policy USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
