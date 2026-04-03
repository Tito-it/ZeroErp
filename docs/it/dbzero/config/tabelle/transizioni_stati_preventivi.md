{% include-markdown "it/dbzero/config/manual/transizioni_stati_preventivi.md" %}
# 📚 Tabella `transizioni_stati_preventivi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| stato_da_id | bigint | NO |  |
| stato_a_id | bigint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_transizioni_stati_prev_da_diverso_a |  |
| FOREIGN KEY | fk_transizioni_stati_prev_a | stato_a_id |
| FOREIGN KEY | fk_transizioni_stati_prev_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_preventivi | id |
| UNIQUE | uq_transizioni_stati_preventivi | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_preventivi | `CREATE UNIQUE INDEX pk_transizioni_stati_preventivi ON config.transizioni_stati_preventivi USING btree (id)` |
| uq_transizioni_stati_preventivi | `CREATE UNIQUE INDEX uq_transizioni_stati_preventivi ON config.transizioni_stati_preventivi USING btree (stato_da_id, stato_a_id)` |

---
{% include-markdown "signature-core.md" %}
