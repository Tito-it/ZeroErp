{% include-markdown "it/dbzero/config/manual/iva.md" %}
# 📚 Tabella `iva`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| descrizione | character varying(80) | NO |  |
| descrizione_breve | character varying(40) | NO |  |
| aliquota_iva | numeric(5,2) | NO | 0 |
| natura_iva_id | integer | YES |  |
| conto_iva_acquisti_id | integer | YES |  |
| conto_iva_vendita_id | integer | YES |  |
| id_iva_split | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| attivo | boolean | NO | true |
| storicizza | boolean | YES | true |
| assoggettamento_id | bigint | YES |  |
| codice_interno | character varying(20) | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_iva_aliquota_iva_finito |  |
| CHECK | chk_iva_aliquota_pos_no_natura_assogg |  |
| CHECK | chk_iva_codice_interno_non_vuoto |  |
| CHECK | chk_iva_zero_requires_natura_or_assogg |  |
| FOREIGN KEY | fk_iva_assoggettamento | assoggettamento_id |
| FOREIGN KEY | fk_iva_conto_acq | conto_iva_acquisti_id |
| FOREIGN KEY | fk_iva_conto_ven | conto_iva_vendita_id |
| FOREIGN KEY | fk_iva_natura | natura_iva_id |
| FOREIGN KEY | fk_iva_split | id_iva_split |
| PRIMARY KEY | pk_iva | id |
| UNIQUE | uq_iva_codice | codice |
| UNIQUE | uq_iva_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_iva_desc | `CREATE INDEX ix_iva_desc ON config.iva USING btree (descrizione)` |
| pk_iva | `CREATE UNIQUE INDEX pk_iva ON config.iva USING btree (id)` |
| uq_iva_codice | `CREATE UNIQUE INDEX uq_iva_codice ON config.iva USING btree (codice)` |
| uq_iva_codice_interno | `CREATE UNIQUE INDEX uq_iva_codice_interno ON config.iva USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_iva_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_contratti_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe_componenti', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_ddt_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_ddt_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_componenti', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_fatture_riepiloghi_iva_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_riepiloghi_iva', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_iva_assoggettamenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva_assoggettamenti', 'attivo', 'assoggettamento_id', 'id')` |
| trg_iva_a10_iva_assoggettamenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva_assoggettamenti', 'attivo', 'assoggettamento_id', 'id')` |
| trg_iva_a10_iva_stati_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'iva_stati', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_listini_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe_componenti', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE', 'aliquota_iva', 'E_IVA_TRATTAMENTO_IMMUTABILE', 'assoggettamento_id', 'E_IVA_TRATTAMENTO_IMMUTABILE', 'natura_iva_id', 'E_IVA_TRATTAMENTO_IMMUTABILE')` |
| trg_iva_a10_offerte_commerciali_eccezioni_componenti_blo_8c83e5 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali_eccezioni_componenti', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_ordini_righe_block_deact_upd_99621c | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_ordini_righe_block_deact_upd_c23bd0 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini_righe', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_ordini_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe_componenti', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_preventivi_riepiloghi_iva_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_riepiloghi_iva', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_preventivi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_preventivi_righe_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe_componenti', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_soggetti_titoli_iva_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_titoli_iva', 'iva_id', 'id', 'attivo')` |
| trg_iva_a10_tipi_utenze_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'tipi_utenze', 'iva_id', 'id', 'attivo')` |
| trg_iva_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_iva_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_iva_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_iva_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_iva_guard_conti_iva_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_iva_guard_conti_iva()` |
| trg_iva_guard_conti_iva_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_iva_guard_conti_iva()` |
| trg_iva_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('iva_id')` |
| trg_iva_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('iva_id')` |

---
{% include-markdown "signature-core.md" %}
