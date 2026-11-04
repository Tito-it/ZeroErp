{% include-markdown "it/dbzero/vendite/manual/articoli_gruppi.md" %}
# 📚 Tabella `articoli_gruppi`

> 📝 **Descrizione**
>
> Gruppi degli articoli (classificazioni di livello superiore), utili per riepiloghi e fatturazione

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(100) | NO |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_articoli_gruppi | id |
| UNIQUE | uq_articoli_gruppi_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_articoli_gruppi | `CREATE UNIQUE INDEX pk_articoli_gruppi ON vendite.articoli_gruppi USING btree (id)` |
| uq_articoli_gruppi_codice | `CREATE UNIQUE INDEX uq_articoli_gruppi_codice ON vendite.articoli_gruppi USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_gruppi_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'gruppo_voce_id', 'id', 'attivo')` |
| trg_articoli_gruppi_a10_soggetti_titoli_iva_ambiti_block_cb9387 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva_ambiti', 'gruppo_voce_id', 'id', 'attivo')` |
| trg_articoli_gruppi_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_articoli_gruppi_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_articoli_gruppi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_gruppi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
