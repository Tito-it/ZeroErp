{% include-markdown "it/dbzero/config/manual/stati_doc_offerte_transizioni.md" %}

# 📚 Tabella `stati_doc_offerte_transizioni`

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
| CHECK | ck_sdot_da_diverso_a |  |
| FOREIGN KEY | fk_sdot_a | stato_a_id |
| FOREIGN KEY | fk_sdot_da | stato_da_id |
| PRIMARY KEY | pk_stati_doc_offerte_transizioni | id |
| UNIQUE | uq_stati_doc_offerte_transizioni | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_doc_offerte_transizioni | `CREATE UNIQUE INDEX pk_stati_doc_offerte_transizioni ON config.stati_doc_offerte_transizioni USING btree (id)` |
| uq_stati_doc_offerte_transizioni | `CREATE UNIQUE INDEX uq_stati_doc_offerte_transizioni ON config.stati_doc_offerte_transizioni USING btree (stato_da_id, stato_a_id)` |

---
{% include-markdown "signature-core.md" %}
