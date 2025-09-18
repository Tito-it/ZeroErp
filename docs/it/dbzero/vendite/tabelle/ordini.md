# 📚 Tabella `ordini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | YES | gen_random_uuid() |
| soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | integer | YES |  |
| serie | character varying | YES |  |
| numero | character varying | YES |  |
| anno | smallint | YES |  |
| data | date | NO | CURRENT_DATE |
| stato_doc_ordine_id | bigint | NO |  |
| source_tipo_id | bigint | YES |  |
| source_id | uuid | YES |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| giorni_pagamento | smallint | YES |  |
| fine_mese | boolean | YES |  |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| vettore_soggetto_ruolo_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric | YES |  |
| peso_netto | numeric | YES |  |
| volume | numeric | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| targa | character varying | YES |  |
| data_ora_partenza | timestamp with time zone | YES |  |
| data_ora_consegna_prev | timestamp with time zone | YES |  |
| imponibile_tot | numeric | YES |  |
| sconto_tot | numeric | YES |  |
| iva_tot | numeric | YES |  |
| totale_doc | numeric | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ordini_v_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_ordini_v_billing_account | billing_account_id |
| FOREIGN KEY | fk_ordini_v_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_ordini_v_cliente_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_v_mod_add_trasporto | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_ordini_v_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_ordini_v_source_tipo | source_tipo_id |
| FOREIGN KEY | fk_ordini_v_stato_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordini_v_valute | valuta_id |
| PRIMARY KEY | pk_ordini | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_v_cliente_statoid_data | `CREATE INDEX ix_ordini_v_cliente_statoid_data ON vendite.ordini USING btree (soggetto_ruolo_id, stato_doc_ordine_id, data)` |
| ix_ordini_v_statoid | `CREATE INDEX ix_ordini_v_statoid ON vendite.ordini USING btree (stato_doc_ordine_id)` |
| pk_ordini | `CREATE UNIQUE INDEX pk_ordini ON vendite.ordini USING btree (id)` |
| uq_ordini_v_anno_serie_numero | `CREATE UNIQUE INDEX uq_ordini_v_anno_serie_numero ON vendite.ordini USING btree (anno, serie, numero) WHERE (numero IS NOT NULL)` |
| uq_ordini_v_source_fk | `CREATE UNIQUE INDEX uq_ordini_v_source_fk ON vendite.ordini USING btree (source_tipo_id, source_id) WHERE (source_tipo_id IS NOT NULL)` |
| uq_ordini_v_uid | `CREATE UNIQUE INDEX uq_ordini_v_uid ON vendite.ordini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_ordini_v_upd_protect_num | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a10_ordini_v_protect_num()` |

---
{% include-markdown "signature-core.md" %}
