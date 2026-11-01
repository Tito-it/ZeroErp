{% include-markdown "it/dbzero/vendite/manual/contratti_righe.md" %}
# 📚 Tabella `contratti_righe`

> 📝 **Descrizione**
>
> Righe contratto: canoni, una tantum, orari, consumi con regole

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| contratto_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| tipo_erogazione | character varying(16) | YES |  |
| fonte_quantita_attesa | character varying(32) | YES |  |
| periodicita | character varying(32) | YES |  |
| generazione_canone | character varying(32) | YES |  |
| prezzo_unitario | numeric(18,6) | YES |  |
| quantita | numeric(18,6) | YES |  |
| ordine | smallint | YES | 0 |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| qta_operativa | numeric(18,6) | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric(18,6) | YES |  |
| tx_id | uuid | YES |  |
| tipo_eccezione | vendite.tipo_eccezione_contratto | NO |  |
| stato_approvazione_prezzo | config.stato_approvazione_prezzo | YES |  |
| pratica_approvazione_prezzo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_contratti_righe_factor_to_base_finito |  |
| CHECK | chk_contratti_righe_prezzo_unitario_finito |  |
| CHECK | chk_contratti_righe_qta_operativa_finito |  |
| CHECK | chk_contratti_righe_quantita_finito |  |
| CHECK | chk_contrighe_canone_periodicita |  |
| CHECK | chk_contrighe_coerenza_canone |  |
| CHECK | chk_contrighe_erogazione_per_tipo_eccezione |  |
| CHECK | chk_contrighe_esclusione_senza_dati |  |
| CHECK | chk_contrighe_fonte_per_tipo_eccezione |  |
| CHECK | chk_contrighe_prezzo_per_tipo_eccezione |  |
| CHECK | chk_contrighe_qta_operativa_nonzero |  |
| CHECK | chk_contrighe_quantita_per_fonte |  |
| FOREIGN KEY | fk_contratti_righe_erogazione_fonte | tipo_erogazione, fonte_quantita_attesa |
| FOREIGN KEY | fk_contratti_righe_periodicita | periodicita |
| FOREIGN KEY | fk_contratti_righe_uom_operativa_id | uom_operativa_id |
| FOREIGN KEY | fk_contrighe_articoli | articolo_id |
| FOREIGN KEY | fk_contrighe_contratti | contratto_id |
| FOREIGN KEY | fk_contrighe_pratica_approvazione_prezzo | pratica_approvazione_prezzo_id |
| PRIMARY KEY | pk_contratti_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_contratti_righe_articolo_id | `CREATE INDEX ix_vendite_contratti_righe_articolo_id ON vendite.contratti_righe USING btree (articolo_id)` |
| ix_vendite_contratti_righe_contratto_id | `CREATE INDEX ix_vendite_contratti_righe_contratto_id ON vendite.contratti_righe USING btree (contratto_id)` |
| ix_vendite_contratti_righe_stato_approvazione | `CREATE INDEX ix_vendite_contratti_righe_stato_approvazione ON vendite.contratti_righe USING btree (stato_approvazione_prezzo) WHERE (stato_approvazione_prezzo IS NOT NULL)` |
| pk_contratti_righe | `CREATE UNIQUE INDEX pk_contratti_righe ON vendite.contratti_righe USING btree (id)` |
| uq_contrighe_one_aggiunta_per_articolo | `CREATE UNIQUE INDEX uq_contrighe_one_aggiunta_per_articolo ON vendite.contratti_righe USING btree (contratto_id, articolo_id) WHERE (tipo_eccezione = 'AGGIUNTA'::vendite.tipo_eccezione_contratto)` |
| uq_contrighe_one_eccezione_per_articolo | `CREATE UNIQUE INDEX uq_contrighe_one_eccezione_per_articolo ON vendite.contratti_righe USING btree (contratto_id, articolo_id) WHERE (tipo_eccezione = ANY (ARRAY['OVERRIDE'::vendite.tipo_eccezione_contratto, 'ESCLUSIONE'::vendite.tipo_eccezione_contratto, 'ADESIONE'::vendite.tipo_eccezione_contratto]))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a05_guard_esclusione_immutabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_esclusione_immutabile('contratto_id')` |
| trg_contratti_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_contratti_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_contratti_righe_a10_contratti_righe_componenti_block_d46424 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe_componenti', 'riga_contratto_id', 'id', 'attivo')` |
| trg_contratti_righe_a10_default_erogazione_articolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_default_erogazione_da_articolo()` |
| trg_contratti_righe_a10_default_erogazione_articolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_default_erogazione_da_articolo()` |
| trg_contratti_righe_a10_default_fonte_qta_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_default_fonte_qta()` |
| trg_contratti_righe_a10_default_fonte_qta_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_default_fonte_qta()` |
| trg_contratti_righe_a10_default_periodicita_listino_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_default_periodicita_da_listino('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a10_default_periodicita_listino_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_default_periodicita_da_listino('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a10_guard_erogazione_obbligatoria_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_obbligatoria('contratto_id')` |
| trg_contratti_righe_a10_guard_erogazione_obbligatoria_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_obbligatoria('contratto_id')` |
| trg_contratti_righe_a10_guard_erogazione_perimetro_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_perimetro('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a10_guard_erogazione_perimetro_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_erogazione_perimetro('CONTRATTO', 'contratto_id')` |
| trg_contratti_righe_a10_guard_esclusione_senza_dati_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_esclusione_senza_dati('contratto_id')` |
| trg_contratti_righe_a10_guard_pending_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_pending('contratto_id')` |
| trg_contratti_righe_a10_guard_periodicita_canone_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_periodicita_canone('contratto_id')` |
| trg_contratti_righe_a10_guard_periodicita_canone_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_periodicita_canone('contratto_id')` |
| trg_contratti_righe_a10_guard_quantita_per_fonte_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_quantita_per_fonte('contratto_id')` |
| trg_contratti_righe_a10_guard_quantita_per_fonte_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_quantita_per_fonte('contratto_id')` |
| trg_contratti_righe_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('tipo_eccezione', 'E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE')` |
| trg_contratti_righe_a10_note_contratto_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_contratto', 'target_riga_id', 'id', 'attivo')` |
| trg_contratti_righe_a10_qta_from_operativa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'fonte_quantita_attesa')` |
| trg_contratti_righe_a10_qta_from_operativa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_qta_from_operativa('true', 'fonte_quantita_attesa')` |
| trg_contratti_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_contratti_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_operativa_id', 'id')` |
| trg_contratti_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contratti_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contratti_righe_z90_propaga_qta_componenti_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_componenti_propaga_qta('vendite', 'contratti_righe_componenti', 'riga_contratto_id')` |

---
{% include-markdown "signature-core.md" %}
