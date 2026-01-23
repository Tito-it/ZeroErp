{% include-markdown "it/dbzero/vendite/manual/articoli_descrizioni_aggiuntive.md" %}
# 📚 Tabella `articoli_descrizioni_aggiuntive`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | NO |  |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_articoli_descrizioni_aggiuntive_articoli | articolo_id |
| PRIMARY KEY | pk_articoli_descrizioni_aggiuntive | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_descrizione_aggiuntiva | `CREATE INDEX ix_articoli_descrizione_aggiuntiva ON vendite.articoli_descrizioni_aggiuntive USING btree (descrizione) WITH (fillfactor='100', deduplicate_items='true')` |
| ix_articoli_descrizioni_aggiuntive_articolo_ordine | `CREATE INDEX ix_articoli_descrizioni_aggiuntive_articolo_ordine ON vendite.articoli_descrizioni_aggiuntive USING btree (articolo_id, ordine)` |
| ix_vendite_articoli_descrizione_aggiuntiva_trgm | `CREATE INDEX ix_vendite_articoli_descrizione_aggiuntiva_trgm ON vendite.articoli_descrizioni_aggiuntive USING gin (descrizione gin_trgm_ops) WITH (fastupdate='true', gin_pending_list_limit='4194304')` |
| pk_articoli_descrizioni_aggiuntive | `CREATE UNIQUE INDEX pk_articoli_descrizioni_aggiuntive ON vendite.articoli_descrizioni_aggiuntive USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_descrizioni_aggiuntive_a10_articoli_require_73ce13 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_articoli_descrizioni_aggiuntive_a10_articoli_require_73ce13 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_articoli_descrizioni_aggiuntive_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
