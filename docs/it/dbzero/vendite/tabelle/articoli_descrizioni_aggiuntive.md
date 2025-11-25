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
| ix_articoli_descrizioni_aggiuntive_articolo_ordine | `CREATE INDEX ix_articoli_descrizioni_aggiuntive_articolo_ordine ON vendite.articoli_descrizioni_aggiuntive USING btree (articolo_id, ordine)` |
| pk_articoli_descrizioni_aggiuntive | `CREATE UNIQUE INDEX pk_articoli_descrizioni_aggiuntive ON vendite.articoli_descrizioni_aggiuntive USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_descrizioni_aggiuntive_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
