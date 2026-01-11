# 📚 Tabella `tipi_doc_fiscale`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| codice_interno | character varying | NO |  |
| codice_fe | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_doc_fiscale | id |
| UNIQUE | uq_tipi_doc_fiscale_codice | codice |
| UNIQUE | uq_tipi_doc_fiscale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_doc_fiscale_attivo | `CREATE INDEX ix_tipi_doc_fiscale_attivo ON config.tipi_doc_fiscale USING btree (attivo)` |
| pk_tipi_doc_fiscale | `CREATE UNIQUE INDEX pk_tipi_doc_fiscale ON config.tipi_doc_fiscale USING btree (id)` |
| uq_tipi_doc_fiscale_codice | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_codice ON config.tipi_doc_fiscale USING btree (codice)` |
| uq_tipi_doc_fiscale_codice_fe | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_codice_fe ON config.tipi_doc_fiscale USING btree (codice_fe) WHERE (codice_fe IS NOT NULL)` |
| uq_tipi_doc_fiscale_codice_interno | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_codice_interno ON config.tipi_doc_fiscale USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_doc_fiscale_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |

---
{% include-markdown "signature-core.md" %}
