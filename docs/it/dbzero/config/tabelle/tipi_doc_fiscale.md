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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_doc_fiscale | id |
| UNIQUE | uq_tipi_doc_fiscale_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_doc_fiscale_attivo | `CREATE INDEX ix_tipi_doc_fiscale_attivo ON config.tipi_doc_fiscale USING btree (attivo)` |
| pk_tipi_doc_fiscale | `CREATE UNIQUE INDEX pk_tipi_doc_fiscale ON config.tipi_doc_fiscale USING btree (id)` |
| uq_tipi_doc_fiscale_codice | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_codice ON config.tipi_doc_fiscale USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_block_deact_tipi_doc_fiscale_fatture | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'tipo_doc_fiscale_id')` |

---
{% include-markdown "signature-core.md" %}
