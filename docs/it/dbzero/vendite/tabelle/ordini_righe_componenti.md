{% include-markdown "it/dbzero/vendite/manual/ordini_righe_componenti.md" %}
# 📚 Tabella `ordini_righe_componenti`

> 📝 **Descrizione**
>
> Componenti BoM CASO A dell'ordine: una riga per ogni componente attivo e valido della distinta di un articolo composito (modello unificato del 2026-05-13: l'esposizione in fattura e' una regola di presentazione, non un filtro su queste righe). Prezzo proprio negoziabile (L1/L2/L3). Prezzo padre calcolato da trigger come SUM(prezzo_unitario * coeff_qta_snapshot). Snapshot pricing: al push su commessa i prezzi vengono propagati senza ri-chiamare il resolver.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| riga_ordine_id | bigint | NO |  |
| articolo_componente_id | uuid | NO |  |
| componente_id | uuid | NO |  |
| coeff_qta_snapshot | numeric | NO |  |
| quantita | numeric | NO |  |
| uom_operativa_id | bigint | NO |  |
| factor_to_base | numeric | NO | 1 |
| qta_operativa | numeric | YES |  |
| prezzo_unitario | numeric | NO |  |
| iva_id | integer | YES |  |
| origine_prezzo | character varying(30) | NO |  |
| prezzo_resolver_context | jsonb | YES |  |
| stato_approvazione_prezzo | config.stato_approvazione_prezzo | YES |  |
| pratica_approvazione_prezzo_id | bigint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_righe_componenti_coeff_qta_snapshot_finito |  |
| CHECK | chk_ordini_righe_componenti_factor_to_base_finito |  |
| CHECK | chk_ordini_righe_componenti_prezzo_unitario_finito |  |
| CHECK | chk_ordini_righe_componenti_qta_operativa_finito |  |
| CHECK | chk_ordini_righe_componenti_quantita_finito |  |
| CHECK | chk_ordrighe_comp_coeff_qta_pos |  |
| CHECK | chk_ordrighe_comp_origine |  |
| CHECK | chk_ordrighe_comp_quantita_nz |  |
| FOREIGN KEY | fk_ordrighe_comp_articolo_componente | articolo_componente_id |
| FOREIGN KEY | fk_ordrighe_comp_componente | componente_id |
| FOREIGN KEY | fk_ordrighe_comp_iva | iva_id |
| FOREIGN KEY | fk_ordrighe_comp_pratica | pratica_approvazione_prezzo_id |
| FOREIGN KEY | fk_ordrighe_comp_riga | riga_ordine_id |
| FOREIGN KEY | fk_ordrighe_comp_uom | uom_operativa_id |
| PRIMARY KEY | pk_ordrighe_comp | id |
| UNIQUE | uq_ordrighe_comp_riga_art_comp | riga_ordine_id, articolo_componente_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_ordrighe_comp_articolo_componente | `CREATE INDEX ix_vendite_ordrighe_comp_articolo_componente ON vendite.ordini_righe_componenti USING btree (articolo_componente_id)` |
| ix_vendite_ordrighe_comp_componente | `CREATE INDEX ix_vendite_ordrighe_comp_componente ON vendite.ordini_righe_componenti USING btree (componente_id)` |
| ix_vendite_ordrighe_comp_stato_approvazione | `CREATE INDEX ix_vendite_ordrighe_comp_stato_approvazione ON vendite.ordini_righe_componenti USING btree (stato_approvazione_prezzo) WHERE (stato_approvazione_prezzo IS NOT NULL)` |
| pk_ordrighe_comp | `CREATE UNIQUE INDEX pk_ordrighe_comp ON vendite.ordini_righe_componenti USING btree (id)` |
| uq_ordrighe_comp_riga_art_comp | `CREATE UNIQUE INDEX uq_ordrighe_comp_riga_art_comp ON vendite.ordini_righe_componenti USING btree (riga_ordine_id, articolo_componente_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE_VENDITA', 'riga_ordine_id', 'DRAFT', 'RIGA')` |
| trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE_VENDITA', 'riga_ordine_id', 'DRAFT', 'RIGA')` |
| trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE_VENDITA', 'riga_ordine_id', 'DRAFT', 'RIGA')` |
| trg_ordini_righe_componenti_a10_articoli_componenti_requ_2cdade | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli_componenti', 'attivo', 'articolo_componente_id', 'id')` |
| trg_ordini_righe_componenti_a10_articoli_componenti_requ_2cdade | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli_componenti', 'attivo', 'articolo_componente_id', 'id')` |
| trg_ordini_righe_componenti_a10_articoli_require_attivo_425fd3 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id', 'id')` |
| trg_ordini_righe_componenti_a10_articoli_require_attivo_425fd3 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id', 'id')` |
| trg_ordini_righe_componenti_a10_guard_bom_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_guard_coerenza_bom('vendite', 'ordini_righe', 'riga_ordine_id', 'ordini', 'ordine_id', 'data')` |
| trg_ordini_righe_componenti_a10_guard_bom_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_guard_coerenza_bom('vendite', 'ordini_righe', 'riga_ordine_id', 'ordini', 'ordine_id', 'data')` |
| trg_ordini_righe_componenti_a10_guard_pending_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_righe_componenti_guard_pending()` |
| trg_ordini_righe_componenti_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ordini_righe_componenti_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ordini_righe_componenti_a10_ordini_righe_require_att_7fbee8 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ordini_righe', 'attivo', 'riga_ordine_id', 'id')` |
| trg_ordini_righe_componenti_a10_ordini_righe_require_att_7fbee8 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ordini_righe', 'attivo', 'riga_ordine_id', 'id')` |
| trg_ordini_righe_componenti_a10_unita_misura_require_att_50a164 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_ordini_righe_componenti_a10_unita_misura_require_att_50a164 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_ordini_righe_componenti_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_componenti_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_componenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_componenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_componenti_m50_calcola_quantita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_calcola_quantita('vendite', 'ordini_righe', 'riga_ordine_id')` |
| trg_ordini_righe_componenti_m50_calcola_quantita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_calcola_quantita('vendite', 'ordini_righe', 'riga_ordine_id')` |
| trg_ordini_righe_componenti_z90_ricalcola_padre_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_ricalcola_padre('vendite', 'ordini_righe', 'ordini_righe_componenti', 'riga_ordine_id')` |
| trg_ordini_righe_componenti_z90_ricalcola_padre_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_componenti_ricalcola_padre('vendite', 'ordini_righe', 'ordini_righe_componenti', 'riga_ordine_id')` |
| trg_ordini_righe_componenti_z90_ricalcola_padre_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_ricalcola_padre('vendite', 'ordini_righe', 'ordini_righe_componenti', 'riga_ordine_id')` |
| trg_ordrighe_comp_a10_guard_obbligatorio_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_guard_obbligatorio()` |
| trg_ordrighe_comp_a10_prezzo_obbligatorio_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_check_prezzo_obbligatorio()` |
| trg_ordrighe_comp_a10_prezzo_obbligatorio_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_check_prezzo_obbligatorio()` |

---
{% include-markdown "signature-core.md" %}
