{% include-markdown "it/dbzero/vendite/manual/fatture.md" %}
# 📚 Tabella `fatture`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| registro_id | bigint | NO |  |
| anno | smallint | YES |  |
| serie | character varying | YES |  |
| numero | bigint | YES |  |
| data | date | NO | CURRENT_DATE |
| tipo_doc_fiscale_id | bigint | YES |  |
| stato_doc_fiscale_id | bigint | YES |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| reseller_soggetto_ruolo_id | bigint | YES |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| giorni_pagamento | smallint | YES |  |
| fine_mese | boolean | YES |  |
| imponibile_tot | numeric | YES |  |
| imposta_tot | numeric | YES |  |
| bollo_applicato | boolean | YES |  |
| bollo_importo | numeric | YES |  |
| arrotondamento_precedente | numeric | YES |  |
| arrotondamento_attuale | numeric | YES |  |
| totale_escluso_imponibile | numeric | YES |  |
| totale_doc | numeric | YES |  |
| minimo | boolean | NO | false |
| data_contabilizzazione | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| termine_pagamento_id | bigint | YES |  |
| termine_pagamento_snapshot | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_ba | billing_account_id |
| FOREIGN KEY | fk_fatture_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatture_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_fatture_registro | registro_id |
| FOREIGN KEY | fk_fatture_reseller | reseller_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatture_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_fatture_stato_doc_fiscale | stato_doc_fiscale_id |
| FOREIGN KEY | fk_fatture_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_fatture_tipo_doc_fiscale | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_fatture_valuta | valuta_id |
| PRIMARY KEY | pk_fatture | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_ba_data | `CREATE INDEX ix_fatture_ba_data ON vendite.fatture USING btree (billing_account_id, data)` |
| ix_fatture_data_contabile | `CREATE INDEX ix_fatture_data_contabile ON vendite.fatture USING btree (data_contabilizzazione)` |
| ix_fatture_emitt_data | `CREATE INDEX ix_fatture_emitt_data ON vendite.fatture USING btree (emittente_soggetto_ruolo_id, data)` |
| ix_fatture_stato_doc | `CREATE INDEX ix_fatture_stato_doc ON vendite.fatture USING btree (stato_doc_fiscale_id)` |
| pk_fatture | `CREATE UNIQUE INDEX pk_fatture ON vendite.fatture USING btree (id)` |
| uq_fatture_numero | `CREATE UNIQUE INDEX uq_fatture_numero ON vendite.fatture USING btree (registro_id, anno, COALESCE(serie, ''::character varying), numero) WHERE (numero IS NOT NULL)` |
| uq_fatture_uid | `CREATE UNIQUE INDEX uq_fatture_uid ON vendite.fatture USING btree (uid)` |
| uq_fatture_v_sorgente_fk | `CREATE UNIQUE INDEX uq_fatture_v_sorgente_fk ON vendite.fatture USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_a10_protect_num_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_protect_num()` |
| trg_fatture_a11_numerata_non_annulabile_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_numerata_non_annulabile()` |

---
{% include-markdown "signature-core.md" %}
