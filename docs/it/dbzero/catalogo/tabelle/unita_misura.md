{% include-markdown "it/dbzero/catalogo/manual/unita_misura.md" %}
# 📚 Tabella `unita_misura`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('catalogo.unita_misura_id_seq'::regclass) |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_fattura | character varying | YES |  |
| attivo | boolean | NO | true |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_unita_misura | id |
| UNIQUE | uq_unita_misura_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_unita_misura_codice_upper | `CREATE INDEX ix_unita_misura_codice_upper ON catalogo.unita_misura USING btree (upper((codice)::text))` |
| pk_unita_misura | `CREATE UNIQUE INDEX pk_unita_misura ON catalogo.unita_misura USING btree (id)` |
| uq_unita_misura_codice | `CREATE UNIQUE INDEX uq_unita_misura_codice ON catalogo.unita_misura USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soft_del_unita_misura__articoli__fk_articoli_unita_misura | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('catalogo', 'articoli', 'uom_id')` |
| trg_soft_del_unita_misura_articoli_fk_articoli_unita_misura | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('catalogo', 'articoli', 'uom_id')` |
| trg_upd_unita_misura_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
