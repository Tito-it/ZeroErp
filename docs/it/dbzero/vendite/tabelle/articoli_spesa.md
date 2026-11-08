{% include-markdown "it/dbzero/vendite/manual/articoli_spesa.md" %}
# 📚 Tabella `articoli_spesa`

> 📝 **Descrizione**
>
> Collegamento articoli a voci di spesa, utile per riepiloghi di fattura (energia, gas, ecc.).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(100) | NO |  |
| descrizione_fattura | character varying(60) | YES |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_articoli_spesa | id |
| UNIQUE | uq_articoli_spesa_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_articoli_spesa | `CREATE UNIQUE INDEX pk_articoli_spesa ON vendite.articoli_spesa USING btree (id)` |
| uq_articoli_spesa_codice | `CREATE UNIQUE INDEX uq_articoli_spesa_codice ON vendite.articoli_spesa USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_spesa_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'spesa_id', 'id', 'attivo')` |
| trg_articoli_spesa_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_articoli_spesa_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_articoli_spesa_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_spesa_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
