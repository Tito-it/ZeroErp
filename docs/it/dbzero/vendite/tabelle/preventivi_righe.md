# 📚 Tabella `preventivi_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| preventivo_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying | YES |  |
| quantita | numeric | NO |  |
| prezzo_unitario | numeric | NO |  |
| sconto_percentuale | numeric | YES | 0 |
| iva_id | integer | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| ordine | smallint | YES | 0 |
| attivo | boolean | YES | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_prevrighe_quantita_prezzo |  |
| CHECK | chk_prevrighe_sconto |  |
| FOREIGN KEY | fk_preventivi_vendita_r_uom_operativa | uom_operativa_id |
| FOREIGN KEY | fk_prevrighe_articoli | articolo_id |
| FOREIGN KEY | fk_prevrighe_iva | iva_id |
| FOREIGN KEY | fk_prevrighe_preventivi | preventivo_id |
| PRIMARY KEY | pk_preventivi_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_prevrighe_articolo | `CREATE INDEX ix_prevrighe_articolo ON vendite.preventivi_righe USING btree (articolo_id)` |
| ix_prevrighe_preventivo | `CREATE INDEX ix_prevrighe_preventivo ON vendite.preventivi_righe USING btree (preventivo_id)` |
| pk_preventivi_righe | `CREATE UNIQUE INDEX pk_preventivi_righe ON vendite.preventivi_righe USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
