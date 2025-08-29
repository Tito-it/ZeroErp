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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_attivita_competenza_data_logica |  |
| CHECK | chk_attivita_competenza_mese_primo |  |
| CHECK | chk_attivita_quantita_pos |  |
| FOREIGN KEY | fk_attivita_fatturabili_articoli | articolo_id |
| FOREIGN KEY | fk_attivita_fatturabili_billing_account | billing_account_id |
| FOREIGN KEY | fk_attivita_fatturabili_istanze_utilities | istanza_utility_id |
| PRIMARY KEY | attivita_fatturabili_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| attivita_fatturabili_pkey | `CREATE UNIQUE INDEX attivita_fatturabili_pkey ON vendite.attivita_fatturabili USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
