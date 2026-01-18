# 📚 Tabella `stati_doc_ordini`

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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_doc_ordini | id |
| UNIQUE | uq_stati_doc_ordini_codice | codice |
| UNIQUE | uq_stati_doc_ordini_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_ordini_attivo | `CREATE INDEX ix_stati_doc_ordini_attivo ON config.stati_doc_ordini USING btree (attivo)` |
| pk_stati_doc_ordini | `CREATE UNIQUE INDEX pk_stati_doc_ordini ON config.stati_doc_ordini USING btree (id)` |
| uq_stati_doc_ordini_codice | `CREATE UNIQUE INDEX uq_stati_doc_ordini_codice ON config.stati_doc_ordini USING btree (codice)` |
| uq_stati_doc_ordini_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_ordini_codice_interno ON config.stati_doc_ordini USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_ordini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_ordini_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'stato_doc_ordine_id', 'id')` |
| trg_stati_doc_ordini_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'stato_doc_ordine_id', 'id')` |

---
{% include-markdown "signature-core.md" %}
