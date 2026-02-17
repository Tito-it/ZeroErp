{% include-markdown "it/dbzero/vendite/manual/fatture_sdi.md" %}
# 📚 Tabella `fatture_sdi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| tentativo_num | smallint | NO | 1 |
| stato_sdi_id | bigint | NO |  |
| data_invio | timestamp with time zone | YES |  |
| data_ricezione | timestamp with time zone | YES |  |
| identificativo_sdi | character varying | YES |  |
| nome_file | text | YES |  |
| messaggio_errore | text | YES |  |
| critical | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_sdi_tentativo_num |  |
| FOREIGN KEY | fk_fatture_sdi_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_sdi_stato_sdi | stato_sdi_id |
| PRIMARY KEY | pk_fatture_sdi | id |
| UNIQUE | uq_fatture_sdi_fattura_tentativo | fattura_id, tentativo_num |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatture_sdi | `CREATE UNIQUE INDEX pk_fatture_sdi ON vendite.fatture_sdi USING btree (id)` |
| uq_fatture_sdi_fattura_tentativo | `CREATE UNIQUE INDEX uq_fatture_sdi_fattura_tentativo ON vendite.fatture_sdi USING btree (fattura_id, tentativo_num)` |

---
{% include-markdown "signature-core.md" %}
