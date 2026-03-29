{% include-markdown "it/dbzero/config/manual/token_monouso.md" %}
# 📚 Tabella `token_monouso`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| token_hash | character varying | NO |  |
| tipo | character varying | NO |  |
| auth_user_id | integer | NO |  |
| scadenza | timestamp with time zone | NO |  |
| utilizzato | boolean | NO | false |
| utilizzato_at | timestamp with time zone | YES |  |
| ip_utilizzo | inet | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | token_monouso_pkey | id |
| UNIQUE | uq_token_monouso_token_hash | token_hash |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_token_monouso_scadenza | `CREATE INDEX ix_token_monouso_scadenza ON config.token_monouso USING btree (scadenza)` |
| ix_token_monouso_tipo_user_utilizzato | `CREATE INDEX ix_token_monouso_tipo_user_utilizzato ON config.token_monouso USING btree (tipo, auth_user_id, utilizzato)` |
| token_monouso_pkey | `CREATE UNIQUE INDEX token_monouso_pkey ON config.token_monouso USING btree (id)` |
| uq_token_monouso_token_hash | `CREATE UNIQUE INDEX uq_token_monouso_token_hash ON config.token_monouso USING btree (token_hash)` |

---
{% include-markdown "signature-core.md" %}
