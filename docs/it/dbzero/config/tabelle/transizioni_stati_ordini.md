{% include-markdown "it/dbzero/config/manual/transizioni_stati_ordini.md" %}
# 📚 Tabella `transizioni_stati_ordini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
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
| CHECK | ck_transizioni_stati_ord_da_diverso_a |  |
| CHECK | ck_transizioni_stati_ord_meta_ui |  |
| FOREIGN KEY | fk_tso_a | stato_a_id |
| FOREIGN KEY | fk_tso_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_ordini | id |
| UNIQUE | uq_transizioni_stati_ordini | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_ordini | `CREATE UNIQUE INDEX pk_transizioni_stati_ordini ON config.transizioni_stati_ordini USING btree (id)` |
| uq_transizioni_stati_ordini | `CREATE UNIQUE INDEX uq_transizioni_stati_ordini ON config.transizioni_stati_ordini USING btree (stato_da_id, stato_a_id)` |

---
{% include-markdown "signature-core.md" %}
