{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_attivita.md" %}
# 📚 Tabella `fatturazione_lotti_attivita`

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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lotti_attivita_stato |  |
| FOREIGN KEY | fk_fatturazione_lotti_attivita_ba | billing_account_id |
| FOREIGN KEY | fk_fatturazione_lotti_attivita_sorgente | sorgente_tipo_id |
| FOREIGN KEY | fk_fatturazione_lotti_attivita_utility | utility_id |
| PRIMARY KEY | pk_fatturazione_lotti_attivita | id |
| UNIQUE | uq_fatturazione_lotti_attivita_codice | codice |
| UNIQUE | uq_fatturazione_lotti_attivita_lock_batch_id | lock_batch_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti_attivita | `CREATE UNIQUE INDEX pk_fatturazione_lotti_attivita ON vendite.fatturazione_lotti_attivita USING btree (id)` |
| uq_fatturazione_lotti_attivita_codice | `CREATE UNIQUE INDEX uq_fatturazione_lotti_attivita_codice ON vendite.fatturazione_lotti_attivita USING btree (codice)` |
| uq_fatturazione_lotti_attivita_lock_batch_id | `CREATE UNIQUE INDEX uq_fatturazione_lotti_attivita_lock_batch_id ON vendite.fatturazione_lotti_attivita USING btree (lock_batch_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_attivita_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatturazione_lotti_attivita_gen_codice()` |
| trg_fatturazione_lotti_attivita_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatturazione_lotti_attivita_gen_codice()` |
| trg_fatturazione_lotti_attivita_a10_sorgenti_require_att_e6ab3e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_fatturazione_lotti_attivita_a10_sorgenti_require_att_e6ab3e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_fatturazione_lotti_attivita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_attivita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_attivita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_attivita_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_attivita_id')` |
| trg_fatturazione_lotti_attivita_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_attivita_id')` |

---
{% include-markdown "signature-core.md" %}
