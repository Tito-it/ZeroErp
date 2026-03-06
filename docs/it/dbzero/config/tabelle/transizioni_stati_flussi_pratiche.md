{% include-markdown "it/dbzero/config/manual/transizioni_stati_flussi_pratiche.md" %}
# 📚 Tabella `transizioni_stati_flussi_pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| stato_da_id | integer | NO |  |
| stato_a_id | integer | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_transizioni_stati_flussi_pratiche_da_diverso_a |  |
| FOREIGN KEY | fk_transizioni_stati_flussi_pratiche_a | stato_a_id |
| FOREIGN KEY | fk_transizioni_stati_flussi_pratiche_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_flussi_pratiche | id |
| UNIQUE | uq_transizioni_stati_flussi_pratiche | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_flussi_pratiche | `CREATE UNIQUE INDEX pk_transizioni_stati_flussi_pratiche ON config.transizioni_stati_flussi_pratiche USING btree (id)` |
| uq_transizioni_stati_flussi_pratiche | `CREATE UNIQUE INDEX uq_transizioni_stati_flussi_pratiche ON config.transizioni_stati_flussi_pratiche USING btree (stato_da_id, stato_a_id)` |

---
{% include-markdown "signature-core.md" %}
