{% include-markdown "it/dbzero/catalogo/manual/unita_misura.md" %}
# 📚 Tabella `unita_misura`

> 📝 **Descrizione**
>
> Unità di misura standard (interna + descrizione stampa)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(100) | NO |  |
| descrizione_fattura | character varying(100) | YES |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tipo_uom_id | bigint | NO |  |
| conta_dal_calendario | character varying(16) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_unita_misura_conta_dal_calendario |  |
| FOREIGN KEY | fk_unita_misura_tipo_uom | tipo_uom_id |
| PRIMARY KEY | pk_unita_misura | id |
| UNIQUE | uq_unita_misura_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_catalogo_unita_misura_descrizione | `CREATE INDEX ix_catalogo_unita_misura_descrizione ON catalogo.unita_misura USING btree (descrizione) WITH (fillfactor='100', deduplicate_items='true')` |
| pk_unita_misura | `CREATE UNIQUE INDEX pk_unita_misura ON catalogo.unita_misura USING btree (id)` |
| uq_unita_misura_codice | `CREATE UNIQUE INDEX uq_unita_misura_codice ON catalogo.unita_misura USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_unita_misura_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_articoli_uom_operativa_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli_uom_operativa', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_attivita_consumi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_consumi', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_contratti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_contratti_righe_componenti_block_de_2ebae1 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe_componenti', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_ddt_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt_righe', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_ddt_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_componenti', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_guard_tipo_uom_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_unita_misura_guard_tipo_update()` |
| trg_unita_misura_a10_listini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_offerte_commerciali_eccezioni_block_ce1c7b | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali_eccezioni', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_offerte_commerciali_eccezioni_compo_1ae18e | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali_eccezioni_componenti', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini_righe', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_ordini_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe_componenti', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_preventivi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_preventivi_righe_componenti_block_d_34c143 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe_componenti', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_promo_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'promo_articoli', 'uom_id', 'id', 'attivo')` |
| trg_unita_misura_a10_resi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe', 'uom_operativa_id', 'id', 'attivo')` |
| trg_unita_misura_a10_unita_misura_conversioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'unita_misura_conversioni', 'uom_from_id', 'id', 'attivo')` |
| trg_unita_misura_a10_uom_tipi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'uom_tipi', 'attivo', 'tipo_uom_id', 'id')` |
| trg_unita_misura_a10_uom_tipi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'uom_tipi', 'attivo', 'tipo_uom_id', 'id')` |
| trg_unita_misura_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_unita_misura_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_unita_misura_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_unita_misura_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
