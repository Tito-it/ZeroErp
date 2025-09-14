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
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_sorgenti_codice_interno_non_vuoto |  |
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
| trg_block_deact_sorgenti_attivita_fatturabili | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'sorgente_tipo_id')` |
| trg_block_deact_sorgenti_fatture | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'sorgente_tipo_id')` |
| trg_block_deact_sorgenti_fatture_righe | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_righe', 'sorgente_tipo_id')` |
| trg_block_deact_sorgenti_ordini | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'source_tipo_id')` |
| trg_block_deact_sorgenti_ordini_righe | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe', 'sorgente_tipo_id')` |
| trg_sorgenti_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_sorgenti_norm()` |
| trg_sorgenti_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_sorgenti_norm()` |
| trg_sorgenti_upd_lock_categoria | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('categoria', 'CODICE_NON_MODIFICABILE')` |
| trg_sorgenti_upd_lock_cod_interno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_sorgenti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
