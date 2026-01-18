{% include-markdown "it/dbzero/vendite/manual/articoli_tipologie.md" %}
# 📚 Tabella `articoli_tipologie`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | YES |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
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
| pk_articoli_tipologie | `CREATE UNIQUE INDEX pk_articoli_tipologie ON vendite.articoli_tipologie USING btree (id)` |
| uq_articoli_tipologie_codice | `CREATE UNIQUE INDEX uq_articoli_tipologie_codice ON vendite.articoli_tipologie USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_tipologie_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'tipo_voce_id', 'id')` |
| trg_articoli_tipologie_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
