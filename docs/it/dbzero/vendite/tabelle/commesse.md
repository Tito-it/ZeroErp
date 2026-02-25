{% include-markdown "it/dbzero/vendite/manual/commesse.md" %}
# 📚 Tabella `commesse`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| tipo_commessa | character varying | NO | 'AUTO'::character varying |
| stato_commessa | character varying | NO | 'BOZZA'::character varying |
| policy_fatturazione | character varying | NO | 'DA_DOCUMENTO'::character varying |
| fatturazione_immediata | boolean | NO | false |
| priorita_operativa | character varying | NO | 'NORMALE'::character varying |
| billing_account_id | bigint | NO |  |
| utility_id | integer | NO |  |
| emittente_soggetto_ruolo_id | bigint | YES |  |
| competenza_dal | date | YES |  |
| competenza_al | date | YES |  |
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
| CHECK | chk_commesse_competenza_range |  |
| CHECK | chk_commesse_policy |  |
| CHECK | chk_commesse_priorita |  |
| CHECK | chk_commesse_stato |  |
| CHECK | chk_commesse_tipo |  |
| FOREIGN KEY | fk_commesse_billing_account | billing_account_id |
| FOREIGN KEY | fk_commesse_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_commesse_utility | utility_id |
| PRIMARY KEY | pk_commesse | id |
| UNIQUE | uq_commesse_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_ba_utility | `CREATE INDEX ix_commesse_ba_utility ON vendite.commesse USING btree (billing_account_id, utility_id)` |
| ix_commesse_stato | `CREATE INDEX ix_commesse_stato ON vendite.commesse USING btree (stato_commessa)` |
| pk_commesse | `CREATE UNIQUE INDEX pk_commesse ON vendite.commesse USING btree (id)` |
| uq_commesse_codice | `CREATE UNIQUE INDEX uq_commesse_codice ON vendite.commesse USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
