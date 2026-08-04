# 📚 Tabella `user_emittente_attivo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| emittente_fiscale_id | bigint | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_user_emittente_attivo_emittente | emittente_fiscale_id |
| PRIMARY KEY | pk_user_emittente_attivo | id |
| UNIQUE | uq_user_emittente_attivo_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_user_emittente_attivo | `CREATE UNIQUE INDEX pk_user_emittente_attivo ON config.user_emittente_attivo USING btree (id)` |
| uq_user_emittente_attivo_auth_user | `CREATE UNIQUE INDEX uq_user_emittente_attivo_auth_user ON config.user_emittente_attivo USING btree (auth_user_id)` |

---
{% include-markdown "signature-core.md" %}
