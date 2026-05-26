{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali_eccezioni_componenti.md" %}
# 📚 Tabella `offerte_commerciali_eccezioni_componenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| eccezione_offerta_id | bigint | NO |  |
| articolo_componente_id | uuid | NO |  |
| componente_id | uuid | NO |  |
| coeff_qta_snapshot | numeric | NO |  |
| quantita | numeric | NO |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |
| qta_operativa | numeric | YES |  |
| prezzo_unitario | numeric | NO |  |
| iva_id | integer | YES |  |
| origine_prezzo | character varying | NO |  |
| prezzo_resolver_context | jsonb | YES |  |
| stato_approvazione_prezzo | USER-DEFINED | YES |  |
| pratica_approvazione_prezzo_id | bigint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| ordine | smallint | YES | 0 |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_oce_comp_coeff_qta_pos |  |
| CHECK | chk_oce_comp_origine |  |
| CHECK | chk_oce_comp_quantita_nz |  |
| FOREIGN KEY | fk_oce_comp_art_comp | articolo_componente_id |
| FOREIGN KEY | fk_oce_comp_componente | componente_id |
| FOREIGN KEY | fk_oce_comp_eccezione | eccezione_offerta_id |
| FOREIGN KEY | fk_oce_comp_iva | iva_id |
| FOREIGN KEY | fk_oce_comp_pratica | pratica_approvazione_prezzo_id |
| FOREIGN KEY | fk_oce_comp_uom | uom_operativa_id |
| PRIMARY KEY | pk_oce_comp | id |
| UNIQUE | uq_oce_comp_eccezione_art_comp | eccezione_offerta_id, articolo_componente_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_oce_comp_art_comp | `CREATE INDEX ix_vendite_oce_comp_art_comp ON vendite.offerte_commerciali_eccezioni_componenti USING btree (articolo_componente_id)` |
| ix_vendite_oce_comp_componente | `CREATE INDEX ix_vendite_oce_comp_componente ON vendite.offerte_commerciali_eccezioni_componenti USING btree (componente_id)` |
| ix_vendite_oce_comp_eccezione | `CREATE INDEX ix_vendite_oce_comp_eccezione ON vendite.offerte_commerciali_eccezioni_componenti USING btree (eccezione_offerta_id)` |
| ix_vendite_oce_comp_stato_appr | `CREATE INDEX ix_vendite_oce_comp_stato_appr ON vendite.offerte_commerciali_eccezioni_componenti USING btree (stato_approvazione_prezzo) WHERE (stato_approvazione_prezzo IS NOT NULL)` |
| pk_oce_comp | `CREATE UNIQUE INDEX pk_oce_comp ON vendite.offerte_commerciali_eccezioni_componenti USING btree (id)` |
| uq_oce_comp_eccezione_art_comp | `CREATE UNIQUE INDEX uq_oce_comp_eccezione_art_comp ON vendite.offerte_commerciali_eccezioni_componenti USING btree (eccezione_offerta_id, articolo_componente_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_oce_comp_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id', 'id')` |
| trg_oce_comp_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id', 'id')` |
| trg_oce_comp_a10_guard_bom_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_guard_coerenza_bom('vendite', 'offerte_commerciali_eccezioni', 'eccezione_offerta_id', 'offerte_commerciali', 'offerta_id', 'validita_dal')` |
| trg_oce_comp_a10_guard_bom_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_guard_coerenza_bom('vendite', 'offerte_commerciali_eccezioni', 'eccezione_offerta_id', 'offerte_commerciali', 'offerta_id', 'validita_dal')` |
| trg_oce_comp_a10_guard_obbligatorio_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_guard_obbligatorio()` |
| trg_oce_comp_a10_guard_pending_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_guard_pending('eccezione_offerta_id')` |
| trg_oce_comp_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_oce_comp_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_oce_comp_a10_prezzo_obbligatorio_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_check_prezzo_obbligatorio()` |
| trg_oce_comp_a10_prezzo_obbligatorio_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_check_prezzo_obbligatorio()` |
| trg_oce_comp_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_oce_comp_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_oce_comp_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_oce_comp_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_oce_comp_m50_calcola_quantita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_calcola_quantita('vendite', 'offerte_commerciali_eccezioni', 'eccezione_offerta_id')` |
| trg_oce_comp_m50_calcola_quantita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_calcola_quantita('vendite', 'offerte_commerciali_eccezioni', 'eccezione_offerta_id')` |
| trg_oce_comp_z90_ricalcola_padre_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_componenti_ricalcola_padre('vendite', 'offerte_commerciali_eccezioni', 'offerte_commerciali_eccezioni_componenti', 'eccezione_offerta_id')` |
| trg_oce_comp_z90_ricalcola_padre_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_componenti_ricalcola_padre('vendite', 'offerte_commerciali_eccezioni', 'offerte_commerciali_eccezioni_componenti', 'eccezione_offerta_id')` |
| trg_oce_comp_z90_ricalcola_padre_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_ricalcola_padre('vendite', 'offerte_commerciali_eccezioni', 'offerte_commerciali_eccezioni_componenti', 'eccezione_offerta_id')` |

---
{% include-markdown "signature-core.md" %}
