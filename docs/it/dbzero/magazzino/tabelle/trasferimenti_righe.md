# 📚 Tabella `trasferimenti_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| trasferimento_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| qta | numeric | NO |  |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_trasferimenti_qta_pos |  |
| FOREIGN KEY | fk_mag_trasferimenti_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_trasferimenti_righe_testata | trasferimento_id |
| PRIMARY KEY | pk_mag_trasferimenti_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_trasferimenti_r_articolo | `CREATE INDEX ix_mag_trasferimenti_r_articolo ON magazzino.trasferimenti_righe USING btree (articolo_id)` |
| pk_mag_trasferimenti_righe | `CREATE UNIQUE INDEX pk_mag_trasferimenti_righe ON magazzino.trasferimenti_righe USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
