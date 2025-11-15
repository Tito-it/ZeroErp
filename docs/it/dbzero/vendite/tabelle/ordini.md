{% include-markdown "it/dbzero/vendite/manual/ordini.md" %}
# 📚 Tabella `ordini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | integer | YES |  |
| serie | character varying | YES |  |
| numero | character varying | YES |  |
| anno | smallint | YES |  |
| data | date | NO | CURRENT_DATE |
| stato_doc_ordine_id | bigint | NO |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
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
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| termine_pagamento_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ordini_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_ordini_v_billing_account | billing_account_id |
| FOREIGN KEY | fk_ordini_v_cliente_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_v_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_ordini_v_sorgente_tipo | sorgente_tipo_id |
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
| uq_ordini_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_v_sorgente_fk ON vendite.ordini USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |
| uq_ordini_v_uid | `CREATE UNIQUE INDEX uq_ordini_v_uid ON vendite.ordini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_a10_upd_v_protect_num | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a10_ordini_v_protect_num()` |
| trg_ordini_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_norm()` |
| trg_ordini_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_norm()` |

---
{% include-markdown "signature-core.md" %}
