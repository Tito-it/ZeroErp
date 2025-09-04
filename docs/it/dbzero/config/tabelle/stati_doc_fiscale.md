# 📚 Tabella `stati_doc_fiscale`

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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_doc_fiscale | id |
| UNIQUE | uq_stati_doc_fiscale_codice | codice |
| UNIQUE | uq_stati_doc_fiscale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_fiscale_attivo | `CREATE INDEX ix_stati_doc_fiscale_attivo ON config.stati_doc_fiscale USING btree (attivo)` |
| pk_stati_doc_fiscale | `CREATE UNIQUE INDEX pk_stati_doc_fiscale ON config.stati_doc_fiscale USING btree (id)` |
| uq_stati_doc_fiscale_codice | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_codice ON config.stati_doc_fiscale USING btree (codice)` |
| uq_stati_doc_fiscale_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_codice_interno ON config.stati_doc_fiscale USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_block_deact_stati_doc_fiscale_fatture | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'stato_doc_fiscale_id')` |
| trg_stati_doc_fiscale_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |

---
{% include-markdown "signature-core.md" %}
