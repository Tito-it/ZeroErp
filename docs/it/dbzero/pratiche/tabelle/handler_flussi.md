{% include-markdown "it/dbzero/pratiche/manual/handler_flussi.md" %}
# 📚 Tabella `handler_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| handler_key | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_pratiche_handler_flussi | id |
| UNIQUE | uq_pratiche_handler_flussi_codice | codice |
| UNIQUE | uq_pratiche_handler_flussi_handler_key | handler_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_handler_flussi | `CREATE UNIQUE INDEX pk_pratiche_handler_flussi ON pratiche.handler_flussi USING btree (id)` |
| uq_pratiche_handler_flussi_codice | `CREATE UNIQUE INDEX uq_pratiche_handler_flussi_codice ON pratiche.handler_flussi USING btree (codice)` |
| uq_pratiche_handler_flussi_handler_key | `CREATE UNIQUE INDEX uq_pratiche_handler_flussi_handler_key ON pratiche.handler_flussi USING btree (handler_key)` |

---
{% include-markdown "signature-core.md" %}
