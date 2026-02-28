{% include-markdown "it/dbzero/config/manual/user_override_azioni.md" %}
# 📚 Tabella `user_override_azioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| azione_id | integer | NO |  |
| abilitata | boolean | NO |  |
| motivo | text | YES |  |
| valido_dal | date | YES | CURRENT_DATE |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_user_override_azioni_validita |  |
| FOREIGN KEY | fk_user_override_azioni_azione | azione_id |
| PRIMARY KEY | pk_user_override_azioni | id |
| UNIQUE | uq_user_override_azioni_user_azione | auth_user_id, azione_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_user_override_azioni_auth_user_id | `CREATE INDEX ix_user_override_azioni_auth_user_id ON config.user_override_azioni USING btree (auth_user_id)` |
| ix_user_override_azioni_azione_id | `CREATE INDEX ix_user_override_azioni_azione_id ON config.user_override_azioni USING btree (azione_id)` |
| pk_user_override_azioni | `CREATE UNIQUE INDEX pk_user_override_azioni ON config.user_override_azioni USING btree (id)` |
| uq_user_override_azioni_user_azione | `CREATE UNIQUE INDEX uq_user_override_azioni_user_azione ON config.user_override_azioni USING btree (auth_user_id, azione_id)` |

---
{% include-markdown "signature-core.md" %}
