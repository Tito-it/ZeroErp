{% include-markdown "it/dbzero/config/manual/user_emittenti_fiscali.md" %}
# 📚 Tabella `user_emittenti_fiscali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_user_emittenti_fiscali_emittente | emittente_fiscale_id |
| PRIMARY KEY | pk_user_emittenti_fiscali | id |
| UNIQUE | uq_user_emittenti_fiscali_user_emittente | auth_user_id, emittente_fiscale_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_user_emittenti_fiscali_auth_user_id | `CREATE INDEX ix_user_emittenti_fiscali_auth_user_id ON config.user_emittenti_fiscali USING btree (auth_user_id)` |
| ix_user_emittenti_fiscali_emittente_id | `CREATE INDEX ix_user_emittenti_fiscali_emittente_id ON config.user_emittenti_fiscali USING btree (emittente_fiscale_id)` |
| pk_user_emittenti_fiscali | `CREATE UNIQUE INDEX pk_user_emittenti_fiscali ON config.user_emittenti_fiscali USING btree (id)` |
| uq_user_emittenti_fiscali_user_emittente | `CREATE UNIQUE INDEX uq_user_emittenti_fiscali_user_emittente ON config.user_emittenti_fiscali USING btree (auth_user_id, emittente_fiscale_id)` |

---
{% include-markdown "signature-core.md" %}
