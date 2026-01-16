# 📚 Tabella `ordini_righe_fulfillment`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_riga_id | bigint | NO |  |
| ddt_riga_id | bigint | NO |  |
| qta_ricevuta | numeric | NO |  |
| note | character varying | YES |  |
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
| CHECK | chk_ordini_ful_a_qta_pos |  |
| FOREIGN KEY | fk_ordini_ful_a_ddt_riga | ddt_riga_id |
| FOREIGN KEY | fk_ordini_ful_a_ordine_riga | ordine_riga_id |
| PRIMARY KEY | pk_fula | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_acquisti_ordini_righe_fulfillment_ddt_riga_id | `CREATE INDEX ix_acquisti_ordini_righe_fulfillment_ddt_riga_id ON acquisti.ordini_righe_fulfillment USING btree (ddt_riga_id)` |
| pk_fula | `CREATE UNIQUE INDEX pk_fula ON acquisti.ordini_righe_fulfillment USING btree (id)` |
| uq_ordini_ful_a_pair | `CREATE UNIQUE INDEX uq_ordini_ful_a_pair ON acquisti.ordini_righe_fulfillment USING btree (ordine_riga_id, ddt_riga_id)` |

---
{% include-markdown "signature-core.md" %}
