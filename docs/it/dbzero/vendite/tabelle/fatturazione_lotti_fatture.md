{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_fatture.md" %}
# 📚 Tabella `fatturazione_lotti_fatture`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| stato_sdi_id | bigint | YES |  |
| esclusa | boolean | NO | false |
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
| FOREIGN KEY | fk_fatturazione_lotti_fatture_fattura | fattura_id |
| FOREIGN KEY | fk_fatturazione_lotti_fatture_lotto | lotto_id |
| FOREIGN KEY | fk_fatturazione_lotti_fatture_stato_sdi | stato_sdi_id |
| PRIMARY KEY | pk_fatturazione_lotti_fatture | id |
| UNIQUE | uq_fatturazione_lotti_fatture_lotto_fattura | lotto_id, fattura_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti_fatture | `CREATE UNIQUE INDEX pk_fatturazione_lotti_fatture ON vendite.fatturazione_lotti_fatture USING btree (id)` |
| uq_fatturazione_lotti_fatture_lotto_fattura | `CREATE UNIQUE INDEX uq_fatturazione_lotti_fatture_lotto_fattura ON vendite.fatturazione_lotti_fatture USING btree (lotto_id, fattura_id)` |

---
{% include-markdown "signature-core.md" %}
