# 📚 Tabella `ordini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | YES | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| serie | character varying | YES |  |
| numero | character varying | YES |  |
| anno | smallint | YES |  |
| data | date | NO | CURRENT_DATE |
| stato_doc_ordine_id | bigint | NO |  |
| sorgente_tipo_id | bigint | YES |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| giorni_pagamento | smallint | YES |  |
| fine_mese | boolean | YES |  |
| indirizzo_consegna_id | integer | NO |  |
| indirizzo_cons_snapshot | jsonb | NO | '{}'::jsonb |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric | YES |  |
| peso_netto | numeric | YES |  |
| volume | numeric | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| data_ora_consegna_prev | timestamp with time zone | YES |  |
| imponibile_tot_atteso | numeric | YES |  |
| sconto_tot_atteso | numeric | YES |  |
| iva_tot_atteso | numeric | YES |  |
| totale_doc_atteso | numeric | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| hash_contenuto | character varying | YES |  |
| sorgente_uid | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_ao_totali_nonneg |  |
| FOREIGN KEY | fk_ao_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_ao_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_ao_matr | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_ao_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ao_stato_doc_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordini_ao_fornitore_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_ao_indir_cons | indirizzo_consegna_id |
| FOREIGN KEY | fk_ordini_ao_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_ordini_ao_valute | valuta_id |
| PRIMARY KEY | pk_ordini_a | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ao_stato_doc_ordine | `CREATE INDEX ix_ao_stato_doc_ordine ON acquisti.ordini USING btree (stato_doc_ordine_id)` |
| ix_ordini_ao_fornitore_stato_data | `CREATE INDEX ix_ordini_ao_fornitore_stato_data ON acquisti.ordini USING btree (soggetto_ruolo_id, stato_doc_ordine_id, data)` |
| pk_ordini_a | `CREATE UNIQUE INDEX pk_ordini_a ON acquisti.ordini USING btree (id)` |
| uq_ordini_ao_anno_serie_numero | `CREATE UNIQUE INDEX uq_ordini_ao_anno_serie_numero ON acquisti.ordini USING btree (anno, serie, numero) WHERE (numero IS NOT NULL)` |
| uq_ordini_ao_uid | `CREATE UNIQUE INDEX uq_ordini_ao_uid ON acquisti.ordini USING btree (uid)` |
| uq_ordini_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_v_sorgente_fk ON acquisti.ordini USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_a10_ins_upd_ao_only_consegna_tipo_con | BEFORE | INSERT | `EXECUTE FUNCTION acquisti.trgfn_a10_ao_only_consegna_tipo_con()` |
| trg_ordini_a10_ins_upd_ao_only_consegna_tipo_con | BEFORE | UPDATE | `EXECUTE FUNCTION acquisti.trgfn_a10_ao_only_consegna_tipo_con()` |
| trg_ordini_a10_upd_protect_num | BEFORE | UPDATE | `EXECUTE FUNCTION acquisti.trgfn_a10_ordini_protect_num()` |

---
{% include-markdown "signature-core.md" %}
