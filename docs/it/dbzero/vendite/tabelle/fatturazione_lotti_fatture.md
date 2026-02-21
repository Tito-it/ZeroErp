{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_fatture.md" %}
# 📚 Tabella `fatturazione_lotti_fatture`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| stato_sdi_id | bigint | YES |  |
| esclusa | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| stato_doc_fiscale_id | bigint | YES |  |
| stato_esecuzione | character varying | NO | 'OK'::character varying |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lf_stato_esecuzione |  |
| FOREIGN KEY | fk_fatturazione_lf_stato_doc_fiscale | stato_doc_fiscale_id |
| FOREIGN KEY | fk_fatturazione_lotti_fatture_fattura | fattura_id |
| FOREIGN KEY | fk_fatturazione_lotti_fatture_lotto | lotto_id |
| FOREIGN KEY | fk_fatturazione_lotti_fatture_stato_sdi | stato_sdi_id |
| PRIMARY KEY | pk_fatturazione_lotti_fatture | id |
| UNIQUE | uq_fatturazione_lotti_fatture_lotto_fattura | lotto_id, fattura_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti_fatture | `CREATE UNIQUE INDEX pk_fatturazione_lotti_fatture ON vendite.fatturazione_lotti_fatture USING btree (id)` |
| uq_fatturazione_lotti_fatture_lotto_fattura | `CREATE UNIQUE INDEX uq_fatturazione_lotti_fatture_lotto_fattura ON vendite.fatturazione_lotti_fatture USING btree (lotto_id, fattura_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_fatture_a10_stati_doc_fiscale_req_d84ef3 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id')` |
| trg_fatturazione_lotti_fatture_a10_stati_doc_fiscale_req_d84ef3 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_doc_fiscale_id')` |
| trg_fatturazione_lotti_fatture_a10_stati_sdi_require_att_811d57 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_sdi', 'attivo', 'stato_sdi_id')` |
| trg_fatturazione_lotti_fatture_a10_stati_sdi_require_att_811d57 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_sdi', 'attivo', 'stato_sdi_id')` |
| trg_fatturazione_lotti_fatture_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatturazione_lotti_fatture_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_fatture_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_fatture_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_fatture_id')` |
| trg_fatturazione_lotti_fatture_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatturazione_lotti_fatture_id')` |

---
{% include-markdown "signature-core.md" %}
