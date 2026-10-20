{% include-markdown "it/dbzero/config/manual/sorgenti.md" %}
# 📚 Tabella `sorgenti`

> 📝 **Descrizione**
>
> Dizionario delle sorgenti applicative per collegamenti/idempotenza (ex source/sorgente_tipo).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(50) | NO |  |
| codice | character varying(50) | NO |  |
| categoria | character varying(24) | YES |  |
| descrizione | character varying(160) | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| target_table | regclass | YES |  |
| key_selector | text | NO | 'id'::text |
| tipo_doc_fiscale_id | bigint | YES |  |
| scope | character varying(30) | NO |  |
| area | character varying(30) | YES |  |
| label_selector | character varying(63) | YES |  |
| etichetta | character varying(60) | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_sorgenti_area_non_vuota |  |
| CHECK | chk_sorgenti_codice_interno_non_vuoto |  |
| CHECK | chk_sorgenti_etichetta_non_vuota |  |
| CHECK | chk_sorgenti_key_selector_values |  |
| CHECK | chk_sorgenti_label_selector_identificatore |  |
| CHECK | chk_sorgenti_scope |  |
| FOREIGN KEY | fk_sorgenti_tipo_doc_fiscale | tipo_doc_fiscale_id |
| PRIMARY KEY | sorgenti_pkey | id |
| UNIQUE | uq_sorgenti_codice | codice |
| UNIQUE | uq_sorgenti_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| sorgenti_pkey | `CREATE UNIQUE INDEX sorgenti_pkey ON config.sorgenti USING btree (id)` |
| uq_sorgenti_codice | `CREATE UNIQUE INDEX uq_sorgenti_codice ON config.sorgenti USING btree (codice)` |
| uq_sorgenti_codice_interno | `CREATE UNIQUE INDEX uq_sorgenti_codice_interno ON config.sorgenti USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sorgenti_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'sorgente_origine_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_commesse_sorgenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_sorgenti', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_contratti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_documenti_fatturazione_canali_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'documenti_fatturazione_canali', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_documenti_generati_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'documenti_generati', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_eventi_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'eventi_assets', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_inventari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE', 'categoria', 'E_CODICE_NON_MODIFICABILE')` |
| trg_sorgenti_a10_movimenti_attesi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti_attesi', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini_righe', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_pratiche_sorgenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'pratiche_sorgenti', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_resi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_rettifiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_template_documenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'template_documenti', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_template_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'template_flussi', 'attende_sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_sorgenti_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_sorgenti_a10_trasferimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'trasferimenti', 'sorgente_tipo_id', 'id', 'attivo')` |
| trg_sorgenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sorgenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sorgenti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_sorgenti_normalize()` |
| trg_sorgenti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_sorgenti_normalize()` |

---
{% include-markdown "signature-core.md" %}
