# 📚 Tabella `transizioni_stati_reso`

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
| CHECK | ck_transizioni_stati_reso_da_diverso_a |  |
| CHECK | ck_transizioni_stati_reso_meta_ui |  |
| FOREIGN KEY | fk_tsr_a | stato_a_id |
| FOREIGN KEY | fk_tsr_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_reso | id |
| UNIQUE | uq_transizioni_stati_reso | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_reso | `CREATE UNIQUE INDEX pk_transizioni_stati_reso ON config.transizioni_stati_reso USING btree (id)` |
| uq_transizioni_stati_reso | `CREATE UNIQUE INDEX uq_transizioni_stati_reso ON config.transizioni_stati_reso USING btree (stato_da_id, stato_a_id)` |

---
{% include-markdown "signature-core.md" %}
