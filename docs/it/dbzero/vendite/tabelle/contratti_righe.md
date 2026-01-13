# 📚 Tabella `contratti_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| contratto_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| tipo_erogazione | character varying | YES |  |
| fonte_quantita_attesa | character varying | YES |  |
| periodicita | character varying | YES |  |
| generazione_canone | character varying | YES |  |
| competenza_canone | character varying | YES |  |
| prezzo_unitario | numeric | YES |  |
| quantita_fissa | numeric | YES |  |
| ordine | smallint | YES | 0 |
| attivo | boolean | YES | true |
| meta | jsonb | YES | '{}'::jsonb |
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
| CHECK | chk_contrighe_coerenza_canone |  |
| CHECK | chk_contrighe_fonte_qta |  |
| CHECK | chk_contrighe_tipo_erog |  |
| FOREIGN KEY | fk_contratti_righe_uom_operativa_id | uom_operativa_id |
| FOREIGN KEY | fk_contrighe_articoli | articolo_id |
| FOREIGN KEY | fk_contrighe_contratti | contratto_id |
| PRIMARY KEY | pk_contratti_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_contrighe_articolo | `CREATE INDEX ix_contrighe_articolo ON vendite.contratti_righe USING btree (articolo_id)` |
| ix_contrighe_contratto | `CREATE INDEX ix_contrighe_contratto ON vendite.contratti_righe USING btree (contratto_id)` |
| pk_contratti_righe | `CREATE UNIQUE INDEX pk_contratti_righe ON vendite.contratti_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contratti_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_contratti_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_contratti_righe_a10_note_contratto_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_contratto', 'target_riga_id', 'id')` |
| trg_contratti_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_contratti_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'false')` |
| trg_contratti_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id')` |
| trg_contratti_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id')` |
| trg_contratti_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
