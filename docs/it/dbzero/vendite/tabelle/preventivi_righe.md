# 📚 Tabella `preventivi_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| preventivo_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | YES |  |
| quantita | numeric | NO |  |
| prezzo_unitario | numeric | NO |  |
| sconto_percentuale | numeric | YES | 0 |
| iva_id | integer | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| ordine | smallint | YES | 0 |
| attivo | boolean | YES | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_prevrighe_quantita_prezzo |  |
| CHECK | chk_prevrighe_sconto |  |
| FOREIGN KEY | fk_preventivi_vendita_r_uom_operativa | uom_operativa_id |
| FOREIGN KEY | fk_prevrighe_articoli | articolo_id |
| FOREIGN KEY | fk_prevrighe_iva | iva_id |
| FOREIGN KEY | fk_prevrighe_preventivi | preventivo_id |
| PRIMARY KEY | pk_preventivi_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_preventivi_righe_articolo_id | `CREATE INDEX ix_vendite_preventivi_righe_articolo_id ON vendite.preventivi_righe USING btree (articolo_id)` |
| ix_vendite_preventivi_righe_preventivo_id | `CREATE INDEX ix_vendite_preventivi_righe_preventivo_id ON vendite.preventivi_righe USING btree (preventivo_id)` |
| pk_preventivi_righe | `CREATE UNIQUE INDEX pk_preventivi_righe ON vendite.preventivi_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_preventivi_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_preventivi_righe_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id')` |
| trg_preventivi_righe_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id')` |
| trg_preventivi_righe_a10_note_preventivo_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_preventivo', 'target_riga_id', 'id')` |
| trg_preventivi_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_preventivi_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_preventivi_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id')` |
| trg_preventivi_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id')` |
| trg_preventivi_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
