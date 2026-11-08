{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali_eccezioni.md" %}
# 📚 Tabella `offerte_commerciali_eccezioni`

> 📝 **Descrizione**
>
> Righe dell'offerta commerciale: eccezioni tipizzate rispetto al listino (OVERRIDE = prezzo alternativo, ESCLUSIONE = articolo escluso, AGGIUNTA = articolo fuori listino). Mirror fedele di contratti_righe senza stato_approvazione_prezzo / pratica_approvazione_prezzo_id. La simmetria strutturale garantisce copia 1:1 in fn_push_offerta_a_contratto. rev 2026-05-24.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| offerta_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| tipo_eccezione | vendite.tipo_eccezione_contratto | NO |  |
| tipo_erogazione | character varying(16) | YES |  |
| fonte_quantita_attesa | character varying(32) | YES |  |
| periodicita | character varying(32) | YES |  |
| generazione_canone | character varying(32) | YES |  |
| prezzo_unitario | numeric(18,6) | YES |  |
| quantita | numeric(18,6) | YES |  |
| qta_operativa | numeric(18,6) | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric(18,6) | YES |  |
| ordine | smallint | YES | 0 |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| stato_approvazione_prezzo | config.stato_approvazione_prezzo | YES |  |
| pratica_approvazione_prezzo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_offerte_commerciali_eccezioni_factor_to_base_finito |  |
| CHECK | chk_offerte_commerciali_eccezioni_prezzo_unitario_finito |  |
| CHECK | chk_offerte_commerciali_eccezioni_qta_operativa_finito |  |
| CHECK | chk_offerte_commerciali_eccezioni_quantita_finito |  |
| CHECK | chk_offerte_eccezioni_canone_periodicita |  |
| CHECK | chk_offerte_eccezioni_coerenza_canone |  |
| CHECK | chk_offerte_eccezioni_erogazione_per_tipo_eccezione |  |
| CHECK | chk_offerte_eccezioni_esclusione_senza_dati |  |
| CHECK | chk_offerte_eccezioni_fonte_per_tipo_eccezione |  |
| CHECK | chk_offerte_eccezioni_prezzo_per_tipo_eccezione |  |
| CHECK | chk_offerte_eccezioni_qta_operativa_nonzero |  |
| CHECK | chk_offerte_eccezioni_quantita_per_fonte |  |
| FOREIGN KEY | fk_offerte_commerciali_eccezioni_erogazione_fonte | tipo_erogazione, fonte_quantita_attesa |
| FOREIGN KEY | fk_offerte_commerciali_eccezioni_periodicita | periodicita |
| FOREIGN KEY | fk_offerte_eccezioni_articolo | articolo_id |
| FOREIGN KEY | fk_offerte_eccezioni_offerta | offerta_id |
| FOREIGN KEY | fk_offerte_eccezioni_pratica_approvazione_prezzo | pratica_approvazione_prezzo_id |
| FOREIGN KEY | fk_offerte_eccezioni_uom_operativa | uom_operativa_id |
| PRIMARY KEY | pk_offerte_commerciali_eccezioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_offerte_eccezioni_stato_approvazione | `CREATE INDEX ix_vendite_offerte_eccezioni_stato_approvazione ON vendite.offerte_commerciali_eccezioni USING btree (stato_approvazione_prezzo) WHERE (stato_approvazione_prezzo IS NOT NULL)` |
| pk_offerte_commerciali_eccezioni | `CREATE UNIQUE INDEX pk_offerte_commerciali_eccezioni ON vendite.offerte_commerciali_eccezioni USING btree (id)` |
| uq_offerte_eccezioni_one_aggiunta_per_articolo | `CREATE UNIQUE INDEX uq_offerte_eccezioni_one_aggiunta_per_articolo ON vendite.offerte_commerciali_eccezioni USING btree (offerta_id, articolo_id) WHERE (tipo_eccezione = 'AGGIUNTA'::vendite.tipo_eccezione_contratto)` |
| uq_offerte_eccezioni_one_eccezione_per_articolo | `CREATE UNIQUE INDEX uq_offerte_eccezioni_one_eccezione_per_articolo ON vendite.offerte_commerciali_eccezioni USING btree (offerta_id, articolo_id) WHERE (tipo_eccezione = ANY (ARRAY['OVERRIDE'::vendite.tipo_eccezione_contratto, 'ESCLUSIONE'::vendite.tipo_eccezione_contratto, 'ADESIONE'::vendite.tipo_eccezione_contratto]))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA')` |
| trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA')` |
| trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA')` |
| trg_offerte_commerciali_eccezioni_a05_guard_escl_immut_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_esclusione_immutabile('offerta_id')` |
| trg_offerte_commerciali_eccezioni_a10_articoli_require_a_f5bd6c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_offerte_commerciali_eccezioni_a10_articoli_require_a_f5bd6c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_offerte_commerciali_eccezioni_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('tipo_eccezione', 'E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE')` |
| trg_offerte_commerciali_eccezioni_a10_note_offerte_comme_22884e | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_offerte_commerciali', 'target_riga_id', 'id', 'attivo')` |
| trg_offerte_commerciali_eccezioni_a10_offerte_commercial_160059 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali_eccezioni_componenti', 'eccezione_offerta_id', 'id', 'attivo')` |
| trg_offerte_commerciali_eccezioni_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_offerte_commerciali_eccezioni_a10_unita_misura_requi_4af3a4 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_offerte_commerciali_eccezioni_a10_unita_misura_requi_4af3a4 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_offerte_commerciali_eccezioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_eccezioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_eccezioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_offerte_commerciali_eccezioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_offerte_eccezioni_a10_default_erogazione_articolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_default_erogazione_da_articolo()` |
| trg_offerte_eccezioni_a10_default_erogazione_articolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_default_erogazione_da_articolo()` |
| trg_offerte_eccezioni_a10_default_fonte_qta_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_default_fonte_qta()` |
| trg_offerte_eccezioni_a10_default_fonte_qta_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_default_fonte_qta()` |
| trg_offerte_eccezioni_a10_default_periodicita_listino_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_default_periodicita_da_listino('OFFERTA_COMMERCIALE', 'offerta_id')` |
| trg_offerte_eccezioni_a10_default_periodicita_listino_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_default_periodicita_da_listino('OFFERTA_COMMERCIALE', 'offerta_id')` |
| trg_offerte_eccezioni_a10_guard_articolo_ammesso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('OFFERTA_COMMERCIALE', 'offerta_id')` |
| trg_offerte_eccezioni_a10_guard_articolo_ammesso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('OFFERTA_COMMERCIALE', 'offerta_id')` |
| trg_offerte_eccezioni_a10_guard_erogazione_obbligatoria_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_obbligatoria('offerta_id')` |
| trg_offerte_eccezioni_a10_guard_erogazione_obbligatoria_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_obbligatoria('offerta_id')` |
| trg_offerte_eccezioni_a10_guard_erogazione_perimetro_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_perimetro('OFFERTA_COMMERCIALE', 'offerta_id')` |
| trg_offerte_eccezioni_a10_guard_erogazione_perimetro_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_perimetro('OFFERTA_COMMERCIALE', 'offerta_id')` |
| trg_offerte_eccezioni_a10_guard_esclusione_senza_dati_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_esclusione_senza_dati('offerta_id')` |
| trg_offerte_eccezioni_a10_guard_pending_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_pending('offerta_id')` |
| trg_offerte_eccezioni_a10_guard_periodicita_canone_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_periodicita_canone('offerta_id')` |
| trg_offerte_eccezioni_a10_guard_periodicita_canone_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_periodicita_canone('offerta_id')` |
| trg_offerte_eccezioni_a10_guard_quantita_per_fonte_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_quantita_per_fonte('offerta_id')` |
| trg_offerte_eccezioni_a10_guard_quantita_per_fonte_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_quantita_per_fonte('offerta_id')` |
| trg_offerte_eccezioni_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'fonte_quantita_attesa')` |
| trg_offerte_eccezioni_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'fonte_quantita_attesa')` |
| trg_offerte_eccezioni_z90_propaga_qta_componenti_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_propaga_qta('vendite', 'offerte_commerciali_eccezioni_componenti', 'eccezione_offerta_id')` |

---
{% include-markdown "signature-core.md" %}
