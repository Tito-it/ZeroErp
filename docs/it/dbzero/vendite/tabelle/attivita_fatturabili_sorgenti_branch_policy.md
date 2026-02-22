{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili_sorgenti_branch_policy.md" %}
# 📚 Tabella `attivita_fatturabili_sorgenti_branch_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| branch_code | character varying | NO |  |
| abilitata | boolean | NO | true |
| acquisizione_mode | character varying | NO | 'PUSH'::character varying |
| block_scope | character varying | NO | 'BRANCH'::character varying |
| priorita | smallint | NO | 100 |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_fatt_sorgenti_branch_policy_acquisizione_mode |  |
| CHECK | chk_attivita_fatt_sorgenti_branch_policy_block_scope |  |
| CHECK | chk_attivita_fatt_sorgenti_branch_policy_priorita |  |
| FOREIGN KEY | fk_attivita_fatt_sorgenti_branch_policy_sorgente | sorgente_tipo_id |
| PRIMARY KEY | pk_attivita_fatt_sorgenti_branch_policy | id |
| UNIQUE | uq_attivita_fatt_sorgenti_branch_policy_sorgente | sorgente_tipo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_attivita_fatt_sorgenti_branch_policy_abilitata | `CREATE INDEX ix_attivita_fatt_sorgenti_branch_policy_abilitata ON vendite.attivita_fatturabili_sorgenti_branch_policy USING btree (abilitata) WHERE (attivo IS TRUE)` |
| ix_attivita_fatt_sorgenti_branch_policy_branch | `CREATE INDEX ix_attivita_fatt_sorgenti_branch_policy_branch ON vendite.attivita_fatturabili_sorgenti_branch_policy USING btree (branch_code)` |
| pk_attivita_fatt_sorgenti_branch_policy | `CREATE UNIQUE INDEX pk_attivita_fatt_sorgenti_branch_policy ON vendite.attivita_fatturabili_sorgenti_branch_policy USING btree (id)` |
| uq_attivita_fatt_sorgenti_branch_policy_sorgente | `CREATE UNIQUE INDEX uq_attivita_fatt_sorgenti_branch_policy_sorgente ON vendite.attivita_fatturabili_sorgenti_branch_policy USING btree (sorgente_tipo_id)` |

---
{% include-markdown "signature-core.md" %}
