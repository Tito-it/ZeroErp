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
| sorgente_id | uuid | YES |  |
| sorgente_riga | bigint | YES | 0 |
| posticipa_al | date | YES |  |
| sospesa | boolean | YES | false |
| exclude_reason | character varying | YES |  |
| lock_in_fatturazione | boolean | YES | false |
| lock_batch_id | uuid | YES |  |
| fattura_riga_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_competenza_data_logica |  |
| CHECK | chk_attivita_competenza_mese_primo |  |
| CHECK | chk_attivita_quantita_pos |  |
| FOREIGN KEY | fk_attivita_fatturabili_articoli | articolo_id |
| FOREIGN KEY | fk_attivita_fatturabili_billing_account | billing_account_id |
| FOREIGN KEY | fk_attivita_fatturabili_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_attivita_fatturabili_sorgente_tipo | sorgente_tipo_id |
| PRIMARY KEY | pk_attivita_fatturabili | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_attivita_articolo_flags | `CREATE INDEX ix_attivita_articolo_flags ON vendite.attivita_fatturabili USING btree (articolo_id, approvato, fatturato)` |
| ix_attivita_billing_competenza | `CREATE INDEX ix_attivita_billing_competenza ON vendite.attivita_fatturabili USING btree (billing_account_id, competenza_mese)` |
| ix_attivita_fatturabili_fattura_riga_id | `CREATE INDEX ix_attivita_fatturabili_fattura_riga_id ON vendite.attivita_fatturabili USING btree (fattura_riga_id)` |
| ix_attivita_fatturabili_lock | `CREATE INDEX ix_attivita_fatturabili_lock ON vendite.attivita_fatturabili USING btree (lock_in_fatturazione, lock_batch_id)` |
| ix_attivita_fatturabili_posticipa_sospesa | `CREATE INDEX ix_attivita_fatturabili_posticipa_sospesa ON vendite.attivita_fatturabili USING btree (posticipa_al, sospesa)` |
| ix_attivita_istanza_data | `CREATE INDEX ix_attivita_istanza_data ON vendite.attivita_fatturabili USING btree (istanza_utility_id, data_attivita)` |
| pk_attivita_fatturabili | `CREATE UNIQUE INDEX pk_attivita_fatturabili ON vendite.attivita_fatturabili USING btree (id)` |
| uq_attivita_fatturabili_sorgente_fk | `CREATE UNIQUE INDEX uq_attivita_fatturabili_sorgente_fk ON vendite.attivita_fatturabili USING btree (sorgente_tipo_id, sorgente_id, sorgente_riga)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_attivita_fatturabili_ins_upd_guard_ba_coerenza | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_a10_attivita_fatturabili_ins_upd_guard_ba_coerenza | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()` |
| trg_a10_attivita_fatturabili_ins_upd_guard_fonte | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fonte()` |
| trg_a10_attivita_fatturabili_ins_upd_guard_fonte | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_guard_fonte()` |
| trg_a10_attivita_fatturabili_upd_dlt_guard_fatturato | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a10_attivita_fatturabili_guard_fatturato()` |
| trg_a10_attivita_fatturabili_upd_dlt_guard_fatturato | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_a10_attivita_fatturabili_guard_fatturato()` |
| trg_attivita_fatturabili_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_norm()` |
| trg_attivita_fatturabili_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_attivita_fatturabili_norm()` |

---
{% include-markdown "signature-core.md" %}
