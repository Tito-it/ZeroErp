# 📚 Tabella `stati_doc_offerte`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_doc_offerte | id |
| UNIQUE | uq_stati_doc_offerte_codice | codice |
| UNIQUE | uq_stati_doc_offerte_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_offerte_attivo | `CREATE INDEX ix_stati_doc_offerte_attivo ON config.stati_doc_offerte USING btree (attivo)` |
| pk_stati_doc_offerte | `CREATE UNIQUE INDEX pk_stati_doc_offerte ON config.stati_doc_offerte USING btree (id)` |
| uq_stati_doc_offerte_codice | `CREATE UNIQUE INDEX uq_stati_doc_offerte_codice ON config.stati_doc_offerte USING btree (codice)` |
| uq_stati_doc_offerte_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_offerte_codice_interno ON config.stati_doc_offerte USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
