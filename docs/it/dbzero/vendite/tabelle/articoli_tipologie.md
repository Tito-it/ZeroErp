{% include-markdown "it/dbzero/vendite/manual/articoli_tipologie.md" %}
# 📚 Tabella `articoli_tipologie`

> 📝 **Descrizione**
>
> Tipologie/categorie degli articoli, utili per riepiloghi e fatturazione

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(100) | NO |  |
| descrizione_breve | character varying(60) | YES |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
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
| trg_articoli_tipologie_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'tipo_voce_id', 'id', 'attivo')` |
| trg_articoli_tipologie_a10_soggetti_titoli_iva_ambiti_bl_47bcdf | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva_ambiti', 'tipo_voce_id', 'id', 'attivo')` |
| trg_articoli_tipologie_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_articoli_tipologie_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_articoli_tipologie_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_tipologie_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
