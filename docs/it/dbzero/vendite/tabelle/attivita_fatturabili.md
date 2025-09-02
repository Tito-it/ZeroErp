# 📚 Tabella `attivita_fatturabili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| billing_account_id | integer | YES |  |
| istanza_utility_id | integer | NO |  |
| data_attivita | date | NO |  |
| quantita | numeric | NO |  |
| competenza_mese | date | YES |  |
| competenza_data | date | YES |  |
| approvato | boolean | YES | false |
| fatturato | boolean | YES | false |
| note | character varying | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| sorgente_tipo | character varying | YES |  |
| sorgente_id | uuid | YES |  |
| sorgente_riga | bigint | YES | 0 |
| posticipa_al | date | YES |  |
| sospesa | boolean | YES | false |
| exclude_reason | character varying | YES |  |
| lock_in_fatturazione | boolean | YES | false |
| lock_batch_id | uuid | YES |  |
| fattura_riga_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_competenza_data_logica |  |
| CHECK | chk_attivita_competenza_mese_primo |  |
| CHECK | chk_attivita_quantita_pos |  |
| CHECK | chk_attivita_sorgente_tripla |  |
| FOREIGN KEY | fk_attivita_fatturabili_articoli | articolo_id |
| FOREIGN KEY | fk_attivita_fatturabili_billing_account | billing_account_id |
| FOREIGN KEY | fk_attivita_fatturabili_istanze_utilities | istanza_utility_id |
| PRIMARY KEY | attivita_fatturabili_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| attivita_fatturabili_pkey | `CREATE UNIQUE INDEX attivita_fatturabili_pkey ON vendite.attivita_fatturabili USING btree (id)` |
| ix_attivita_articolo_flags | `CREATE INDEX ix_attivita_articolo_flags ON vendite.attivita_fatturabili USING btree (articolo_id, approvato, fatturato)` |
| ix_attivita_billing_competenza | `CREATE INDEX ix_attivita_billing_competenza ON vendite.attivita_fatturabili USING btree (billing_account_id, competenza_mese)` |
| ix_attivita_fatturabili_fattura_riga_id | `CREATE INDEX ix_attivita_fatturabili_fattura_riga_id ON vendite.attivita_fatturabili USING btree (fattura_riga_id)` |
| ix_attivita_fatturabili_lock | `CREATE INDEX ix_attivita_fatturabili_lock ON vendite.attivita_fatturabili USING btree (lock_in_fatturazione, lock_batch_id)` |
| ix_attivita_fatturabili_posticipa_sospesa | `CREATE INDEX ix_attivita_fatturabili_posticipa_sospesa ON vendite.attivita_fatturabili USING btree (posticipa_al, sospesa)` |
| ix_attivita_fatturabili_sorgente | `CREATE INDEX ix_attivita_fatturabili_sorgente ON vendite.attivita_fatturabili USING btree (sorgente_tipo, sorgente_id)` |
| ix_attivita_istanza_data | `CREATE INDEX ix_attivita_istanza_data ON vendite.attivita_fatturabili USING btree (istanza_utility_id, data_attivita)` |
| uq_af_sorgente | `CREATE UNIQUE INDEX uq_af_sorgente ON vendite.attivita_fatturabili USING btree (sorgente_tipo, sorgente_id, sorgente_riga) WHERE (sorgente_tipo IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_attivita_fatturabili_ins_upd_guard_ba_coerenza | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_a10_attivita_fatturabili_ins_upd_guard_ba_coerenza | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_a10_attivita_fatturabili_ins_upd_guard_fonte | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fonte()` |
| trg_a10_attivita_fatturabili_ins_upd_guard_fonte | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fonte()` |
| trg_a10_attivita_fatturabili_upd_dlt_guard_fatturato | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_a10_attivita_fatturabili_guard_fatturato()` |
| trg_a10_attivita_fatturabili_upd_dlt_guard_fatturato | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a10_attivita_fatturabili_guard_fatturato()` |
| trg_attivita_fatturabili_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_fatturabili_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_norm()` |
| trg_attivita_fatturabili_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_norm()` |
| trg_upd_attivita_fatturabili_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_attivita_fatturabili_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('attivita_fatturabili_id')` |
| trg_z90_attivita_fatturabili_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('attivita_fatturabili_id')` |

---
{% include-markdown "signature-core.md" %}
