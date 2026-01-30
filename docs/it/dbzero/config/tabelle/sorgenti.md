{% include-markdown "it/dbzero/config/manual/sorgenti.md" %}
# 📚 Tabella `sorgenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| categoria | character varying | YES |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| target_table | regclass | YES |  |
| key_selector | text | NO | 'id'::text |
| tipo_doc_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_sorgenti_codice_interno_non_vuoto |  |
| CHECK | chk_sorgenti_key_selector_values |  |
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
| trg_sorgenti_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_eventi_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'eventi_assets', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_fatture_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_inventari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('categoria', 'CODICE_NON_MODIFICABILE')` |
| trg_sorgenti_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_ordini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'sorgente_tipo_id', 'id')` |
| trg_sorgenti_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id')` |
| trg_sorgenti_a10_tipi_doc_fiscale_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id')` |
| trg_sorgenti_a10_trasferimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'trasferimenti', 'sorgenti_tipo_id', 'id')` |
| trg_sorgenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sorgenti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_sorgenti_normalize()` |
| trg_sorgenti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_sorgenti_normalize()` |

---
{% include-markdown "signature-core.md" %}
