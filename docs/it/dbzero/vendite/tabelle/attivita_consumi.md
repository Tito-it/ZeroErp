{% include-markdown "it/dbzero/vendite/manual/attivita_consumi.md" %}
# 📚 Tabella `attivita_consumi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| lotto_attivita_id | bigint | YES |  |
| fattura_id | bigint | YES |  |
| billing_account_id | bigint | NO |  |
| competenza_mese | date | NO |  |
| periodo_dal | date | YES |  |
| periodo_al | date | YES |  |
| consumo_totale | numeric | YES |  |
| uom_id | bigint | YES |  |
| stato_calcolo | text | NO | 'OK'::text |
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
| CHECK | chk_attivita_consumi_stato_calcolo |  |
| FOREIGN KEY | fk_attivita_consumi_ba | billing_account_id |
| FOREIGN KEY | fk_attivita_consumi_fattura | fattura_id |
| FOREIGN KEY | fk_attivita_consumi_lotto_attivita | lotto_attivita_id |
| FOREIGN KEY | fk_attivita_consumi_uom | uom_id |
| PRIMARY KEY | pk_attivita_consumi | id |
| UNIQUE | uq_attivita_consumi_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_attivita_consumi | `CREATE UNIQUE INDEX pk_attivita_consumi ON vendite.attivita_consumi USING btree (id)` |
| uq_attivita_consumi_uid | `CREATE UNIQUE INDEX uq_attivita_consumi_uid ON vendite.attivita_consumi USING btree (uid)` |

---
{% include-markdown "signature-core.md" %}
