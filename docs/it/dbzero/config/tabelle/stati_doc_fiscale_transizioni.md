{% include-markdown "it/dbzero/config/manual/stati_doc_fiscale_transizioni.md" %}
# 📚 Tabella `stati_doc_fiscale_transizioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_from_id | bigint | NO |  |
| stato_to_id | bigint | NO |  |
| ammesso | boolean | NO | true |
| solo_lotto | boolean | NO | false |
| solo_fattura | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_stati_doc_fiscale_transizioni_from | stato_from_id |
| FOREIGN KEY | fk_stati_doc_fiscale_transizioni_to | stato_to_id |
| PRIMARY KEY | pk_stati_doc_fiscale_transizioni | id |
| UNIQUE | uq_stati_doc_fiscale_transizioni | stato_from_id, stato_to_id, solo_lotto, solo_fattura |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_doc_fiscale_transizioni | `CREATE UNIQUE INDEX pk_stati_doc_fiscale_transizioni ON config.stati_doc_fiscale_transizioni USING btree (id)` |
| uq_stati_doc_fiscale_transizioni | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_transizioni ON config.stati_doc_fiscale_transizioni USING btree (stato_from_id, stato_to_id, solo_lotto, solo_fattura)` |

---
{% include-markdown "signature-core.md" %}
