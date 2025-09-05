# 📚 Tabella `fatture`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | gen_random_uuid() |
| registro_id | bigint | NO |  |
| anno | smallint | YES |  |
| serie | character varying | YES |  |
| numero | bigint | YES |  |
| data | date | NO | CURRENT_DATE |
| tipo_doc_fiscale_id | bigint | YES |  |
| stato_doc_fiscale_id | bigint | YES |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| billing_account_id | integer | NO |  |
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
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_id | uuid | YES |  |

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
| uq_fatture_sorgente_fk | `CREATE UNIQUE INDEX uq_fatture_sorgente_fk ON vendite.fatture USING btree (sorgente_tipo_id, sorgente_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_fatture_upd_protect_num | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a10_fatture_protect_num()` |
| trg_a11_fatture_upd_numerata_non_annulabile | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a11_fatture_numerata_non_annulabile()` |
| trg_fatture_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_fatture_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
