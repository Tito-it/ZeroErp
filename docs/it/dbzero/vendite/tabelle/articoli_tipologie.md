{% include-markdown "it/dbzero/vendite/manual/articoli_tipologie.md" %}
# 📚 Tabella `articoli_tipologie`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('vendite.articoli_tipologie_id_seq'::regclass) |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | YES |  |
| attivo | boolean | NO | true |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_articoli_tipologie | id |
| UNIQUE | uq_articoli_tipologie_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_tipologie_codice_upper | `CREATE INDEX ix_articoli_tipologie_codice_upper ON vendite.articoli_tipologie USING btree (upper((codice)::text))` |
| pk_articoli_tipologie | `CREATE UNIQUE INDEX pk_articoli_tipologie ON vendite.articoli_tipologie USING btree (id)` |
| uq_articoli_tipologie_codice | `CREATE UNIQUE INDEX uq_articoli_tipologie_codice ON vendite.articoli_tipologie USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soft_del_articoli_tipologie__articoli__fk_articoli_a_b9278b | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade('catalogo', 'articoli', 'tipo_voce_id')` |
| trg_upd_articoli_tipologie_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
