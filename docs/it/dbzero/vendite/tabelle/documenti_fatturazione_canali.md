{% include-markdown "it/dbzero/vendite/manual/documenti_fatturazione_canali.md" %}
# 📚 Tabella `documenti_fatturazione_canali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | text | NO |  |
| canale_codice | character varying | NO |  |
| stato_canale | character varying | NO | 'APERTO'::character varying |
| target_sorgente_tipo_id | bigint | YES |  |
| target_sorgente_uid | text | YES |  |
| motivo_blocco | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_doc_fatt_canali_canale |  |
| CHECK | chk_doc_fatt_canali_motivo_blocco |  |
| CHECK | chk_doc_fatt_canali_sorgente_uid_not_blank |  |
| CHECK | chk_doc_fatt_canali_stato |  |
| CHECK | chk_doc_fatt_canali_target_pair |  |
| FOREIGN KEY | fk_doc_fatt_canali_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_doc_fatt_canali_target_sorgente_tipo | target_sorgente_tipo_id |
| PRIMARY KEY | pk_documenti_fatturazione_canali | id |
| UNIQUE | uq_doc_fatt_canali_sorgente_canale | sorgente_tipo_id, sorgente_uid, canale_codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_doc_fatt_canali_sorgente | `CREATE INDEX ix_doc_fatt_canali_sorgente ON vendite.documenti_fatturazione_canali USING btree (sorgente_tipo_id, sorgente_uid)` |
| ix_doc_fatt_canali_stato_canale | `CREATE INDEX ix_doc_fatt_canali_stato_canale ON vendite.documenti_fatturazione_canali USING btree (stato_canale, canale_codice)` |
| pk_documenti_fatturazione_canali | `CREATE UNIQUE INDEX pk_documenti_fatturazione_canali ON vendite.documenti_fatturazione_canali USING btree (id)` |
| uq_doc_fatt_canali_sorgente_canale | `CREATE UNIQUE INDEX uq_doc_fatt_canali_sorgente_canale ON vendite.documenti_fatturazione_canali USING btree (sorgente_tipo_id, sorgente_uid, canale_codice)` |
| uq_doc_fatt_canali_un_aperto | `CREATE UNIQUE INDEX uq_doc_fatt_canali_un_aperto ON vendite.documenti_fatturazione_canali USING btree (sorgente_tipo_id, sorgente_uid) WHERE ((stato_canale)::text = 'APERTO'::text)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_documenti_fatturazione_canali_a10_sorgenti_require_a_58ad32 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'target_sorgente_tipo_id')` |
| trg_documenti_fatturazione_canali_a10_sorgenti_require_a_58ad32 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'target_sorgente_tipo_id')` |
| trg_documenti_fatturazione_canali_a10_sorgenti_require_a_d2284f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_documenti_fatturazione_canali_a10_sorgenti_require_a_d2284f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_documenti_fatturazione_canali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_fatturazione_canali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_fatturazione_canali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_documenti_fatturazione_canali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_documenti_fatturazione_canali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('documenti_fatturazione_canali_id')` |
| trg_documenti_fatturazione_canali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('documenti_fatturazione_canali_id')` |

---
{% include-markdown "signature-core.md" %}
