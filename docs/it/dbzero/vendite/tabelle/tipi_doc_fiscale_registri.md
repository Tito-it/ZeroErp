{% include-markdown "it/dbzero/vendite/manual/tipi_doc_fiscale_registri.md" %}
# 📚 Tabella `tipi_doc_fiscale_registri`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_doc_fiscale_id | bigint | NO |  |
| registro_id | bigint | NO |  |
| codice_interno | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| utility_id | integer | YES |  |
| emittente_soggetto_ruolo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_registro | registro_id |
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_tipo_doc | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_utility | utility_id |
| PRIMARY KEY | pk_tipi_doc_fiscale_registri | id |
| UNIQUE | uq_tipi_doc_fiscale_registri_tipo_doc | tipo_doc_fiscale_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_doc_fiscale_registri | `CREATE UNIQUE INDEX pk_tipi_doc_fiscale_registri ON vendite.tipi_doc_fiscale_registri USING btree (id)` |
| uq_tipi_doc_fiscale_registri_tipo_doc | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_registri_tipo_doc ON vendite.tipi_doc_fiscale_registri USING btree (tipo_doc_fiscale_id)` |

---
{% include-markdown "signature-core.md" %}
