{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali_eccezioni.md" %}
# 📚 Tabella `offerte_commerciali_eccezioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| offerta_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| tipo_eccezione | USER-DEFINED | NO |  |
| tipo_erogazione | character varying | YES |  |
| fonte_quantita_attesa | character varying | NO |  |
| periodicita | character varying | YES |  |
| generazione_canone | character varying | YES |  |
| competenza_canone | character varying | YES |  |
| prezzo_unitario | numeric | YES |  |
| quantita | numeric | YES |  |
| qta_operativa | numeric | YES |  |
| uom_operativa_id | bigint | YES |  |
| factor_to_base | numeric | NO | 1 |
| ordine | smallint | YES | 0 |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_offerte_eccezioni_coerenza_canone |  |
| CHECK | chk_offerte_eccezioni_coerenza_fonte_erogazione |  |
| CHECK | chk_offerte_eccezioni_fonte_qta |  |
| CHECK | chk_offerte_eccezioni_prezzo_per_tipo_eccezione |  |
| CHECK | chk_offerte_eccezioni_tipo_erog |  |
| FOREIGN KEY | fk_offerte_eccezioni_articolo | articolo_id |
| FOREIGN KEY | fk_offerte_eccezioni_offerta | offerta_id |
| FOREIGN KEY | fk_offerte_eccezioni_uom_operativa | uom_operativa_id |
| PRIMARY KEY | pk_offerte_commerciali_eccezioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_offerte_commerciali_eccezioni | `CREATE UNIQUE INDEX pk_offerte_commerciali_eccezioni ON vendite.offerte_commerciali_eccezioni USING btree (id)` |
| uq_offerte_eccezioni_one_aggiunta_per_articolo | `CREATE UNIQUE INDEX uq_offerte_eccezioni_one_aggiunta_per_articolo ON vendite.offerte_commerciali_eccezioni USING btree (offerta_id, articolo_id) WHERE (tipo_eccezione = 'AGGIUNTA'::vendite.tipo_eccezione_contratto)` |
| uq_offerte_eccezioni_one_eccezione_per_articolo | `CREATE UNIQUE INDEX uq_offerte_eccezioni_one_eccezione_per_articolo ON vendite.offerte_commerciali_eccezioni USING btree (offerta_id, articolo_id) WHERE (tipo_eccezione = ANY (ARRAY['OVERRIDE'::vendite.tipo_eccezione_contratto, 'ESCLUSIONE'::vendite.tipo_eccezione_contratto]))` |

---
{% include-markdown "signature-core.md" %}
