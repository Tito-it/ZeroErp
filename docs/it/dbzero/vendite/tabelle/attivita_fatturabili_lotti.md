{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili_lotti.md" %}
# 📚 Tabella `attivita_fatturabili_lotti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lock_batch_id | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| competenza_mese | date | NO |  |
| utility_id | integer | YES |  |
| billing_account_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| stato_lotto | text | NO | 'IN_ESECUZIONE'::text |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| stato_operativo | text | NO | 'APERTO'::text |
| emittente_soggetto_ruolo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_fatt_lotti_stato_operativo |  |
| CHECK | chk_attivita_fatturabili_lotti_stato |  |
| FOREIGN KEY | fk_attivita_fatt_lotti_emittente_sr | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_attivita_fatturabili_lotti_ba | billing_account_id |
| FOREIGN KEY | fk_attivita_fatturabili_lotti_sorgente | sorgente_tipo_id |
| FOREIGN KEY | fk_attivita_fatturabili_lotti_utility | utility_id |
| PRIMARY KEY | pk_attivita_fatturabili_lotti | id |
| UNIQUE | uq_attivita_fatturabili_lotti_codice | codice |
| UNIQUE | uq_attivita_fatturabili_lotti_lock_batch_id | lock_batch_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| idx_att_fatt_lotti_stato_operativo | `CREATE INDEX idx_att_fatt_lotti_stato_operativo ON vendite.attivita_fatturabili_lotti USING btree (stato_operativo)` |
| pk_attivita_fatturabili_lotti | `CREATE UNIQUE INDEX pk_attivita_fatturabili_lotti ON vendite.attivita_fatturabili_lotti USING btree (id)` |
| uq_attivita_fatturabili_lotti_codice | `CREATE UNIQUE INDEX uq_attivita_fatturabili_lotti_codice ON vendite.attivita_fatturabili_lotti USING btree (codice)` |
| uq_attivita_fatturabili_lotti_lock_batch_id | `CREATE UNIQUE INDEX uq_attivita_fatturabili_lotti_lock_batch_id ON vendite.attivita_fatturabili_lotti USING btree (lock_batch_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_fatturabili_lotti_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_lotti_gen_codice()` |
| trg_attivita_fatturabili_lotti_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_lotti_gen_codice()` |
| trg_attivita_fatturabili_lotti_a10_sorgenti_require_atti_c93c30 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_attivita_fatturabili_lotti_a10_sorgenti_require_atti_c93c30 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_attivita_fatturabili_lotti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_lotti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_attivita_fatturabili_lotti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_lotti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_lotti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_fatturabili_lotti_id')` |
| trg_attivita_fatturabili_lotti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('attivita_fatturabili_lotti_id')` |

---
{% include-markdown "signature-core.md" %}
