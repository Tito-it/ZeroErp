{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti.md" %}
# 📚 Tabella `fatturazione_lotti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lock_batch_id | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| competenza_mese | date | NO |  |
| utility_id | integer | YES |  |
| registro_id | bigint | YES |  |
| billing_account_id | bigint | YES |  |
| stato_job | text | NO | 'IN_ESECUZIONE'::text |
| stato_documenti | text | NO | 'DRAFT'::text |
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
| CHECK | chk_fatturazione_lotti_stato_documenti |  |
| CHECK | chk_fatturazione_lotti_stato_job |  |
| FOREIGN KEY | fk_fatturazione_lotti_ba | billing_account_id |
| FOREIGN KEY | fk_fatturazione_lotti_registro | registro_id |
| FOREIGN KEY | fk_fatturazione_lotti_utility | utility_id |
| PRIMARY KEY | pk_fatturazione_lotti | id |
| UNIQUE | uq_fatturazione_lotti_codice | codice |
| UNIQUE | uq_fatturazione_lotti_lock_batch_id | lock_batch_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti | `CREATE UNIQUE INDEX pk_fatturazione_lotti ON vendite.fatturazione_lotti USING btree (id)` |
| uq_fatturazione_lotti_codice | `CREATE UNIQUE INDEX uq_fatturazione_lotti_codice ON vendite.fatturazione_lotti USING btree (codice)` |
| uq_fatturazione_lotti_lock_batch_id | `CREATE UNIQUE INDEX uq_fatturazione_lotti_lock_batch_id ON vendite.fatturazione_lotti USING btree (lock_batch_id)` |

---
{% include-markdown "signature-core.md" %}
