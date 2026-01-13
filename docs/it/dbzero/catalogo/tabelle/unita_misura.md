{% include-markdown "it/dbzero/catalogo/manual/unita_misura.md" %}
# 📚 Tabella `unita_misura`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_fattura | character varying | YES |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
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
| trg_unita_misura_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'uom_id', 'id')` |
| trg_unita_misura_a10_articoli_uom_operativa_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_uom_operativa', 'uom_id', 'id')` |
| trg_unita_misura_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'uom_id', 'id')` |
| trg_unita_misura_a10_contratti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe', 'uom_operativa_id', 'id')` |
| trg_unita_misura_a10_ddt_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe', 'uom_operativa_id', 'id')` |
| trg_unita_misura_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'uom_id', 'id')` |
| trg_unita_misura_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'uom_operativa_id', 'id')` |
| trg_unita_misura_a10_preventivi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe', 'uom_operativa_id', 'id')` |
| trg_unita_misura_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
