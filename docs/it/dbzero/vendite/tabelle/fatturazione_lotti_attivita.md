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

---
{% include-markdown "signature-core.md" %}
