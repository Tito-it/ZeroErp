# 📚 Tabella `ddt_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ddt_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | NO |  |
| uom_id | bigint | YES |  |
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
| hash_contenuto | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ddt_acquisto_r_qta_pos |  |
| FOREIGN KEY | fk_ddt_acquisto_r_articolo | articolo_id |
| FOREIGN KEY | fk_ddt_acquisto_r_testata | ddt_id |
| FOREIGN KEY | fk_ddt_acquisto_r_uom | uom_id |
| PRIMARY KEY | pk_ddtar | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_acquisti_ddt_righe_articolo_id | `CREATE INDEX ix_acquisti_ddt_righe_articolo_id ON acquisti.ddt_righe USING btree (articolo_id)` |
| pk_ddtar | `CREATE UNIQUE INDEX pk_ddtar ON acquisti.ddt_righe USING btree (id)` |
| uq_ddt_acquisto_r_riga_nr | `CREATE UNIQUE INDEX uq_ddt_acquisto_r_riga_nr ON acquisti.ddt_righe USING btree (ddt_id, riga_nr)` |

---
{% include-markdown "signature-core.md" %}
