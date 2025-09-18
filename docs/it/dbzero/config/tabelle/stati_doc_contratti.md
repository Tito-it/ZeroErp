# 📚 Tabella `stati_doc_contratti`

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
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_doc_contratti | id |
| UNIQUE | uq_stati_doc_contratti_codice | codice |
| UNIQUE | uq_stati_doc_contratti_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_doc_contratti_attivo | `CREATE INDEX ix_stati_doc_contratti_attivo ON config.stati_doc_contratti USING btree (attivo)` |
| ix_stati_doc_contratti_codice_interno_upper | `CREATE INDEX ix_stati_doc_contratti_codice_interno_upper ON config.stati_doc_contratti USING btree (upper((codice_interno)::text))` |
| ix_stati_doc_contratti_codice_upper | `CREATE INDEX ix_stati_doc_contratti_codice_upper ON config.stati_doc_contratti USING btree (upper((codice)::text))` |
| ix_stati_doc_contratti_descrizione_upper | `CREATE INDEX ix_stati_doc_contratti_descrizione_upper ON config.stati_doc_contratti USING btree (upper((descrizione)::text))` |
| pk_stati_doc_contratti | `CREATE UNIQUE INDEX pk_stati_doc_contratti ON config.stati_doc_contratti USING btree (id)` |
| uq_stati_doc_contratti_codice | `CREATE UNIQUE INDEX uq_stati_doc_contratti_codice ON config.stati_doc_contratti USING btree (codice)` |
| uq_stati_doc_contratti_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_contratti_codice_interno ON config.stati_doc_contratti USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_contratti_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |

---
{% include-markdown "signature-core.md" %}
