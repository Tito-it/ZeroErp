{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali_utilities.md" %}
# 📚 Tabella `offerte_commerciali_utilities`

> 📝 **Descrizione**
>
> Snapshot precontrattuali utility dell'offerta commerciale (1:1). Mirror fedele di contratti_utilities: tutti i campi business inclusi (tipo_utenza_id, classe_utenza_id, param_1_num, param_2_txt, meta, istanza_dati_precontrattuali_id) per copia 1:1 in fn_push_offerta_a_contratto. La coerenza tipo/classe viene verificata solo su contratti_utilities (il guard si applica al momento del push, non sulla proposta). rev 2026-05-24.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| offerta_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| istanza_dati_precontrattuali_id | bigint | YES |  |
| classe_utenza_id | integer | YES |  |
| tipo_utenza_id | integer | YES |  |
| param_1_num | numeric | YES |  |
| param_2_txt | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_offerte_commerciali_utilities_param_1_num_finito |  |
| FOREIGN KEY | fk_offerte_utilities_classe_utenza | classe_utenza_id |
| FOREIGN KEY | fk_offerte_utilities_istanza_dati_precontrattuali | istanza_dati_precontrattuali_id |
| FOREIGN KEY | fk_offerte_utilities_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_offerte_utilities_offerta | offerta_id |
| FOREIGN KEY | fk_offerte_utilities_tipo_utenza | tipo_utenza_id |
| FOREIGN KEY | fk_offerte_utilities_utility | utility_id |
| PRIMARY KEY | pk_offerte_commerciali_utilities | id |
| UNIQUE | uq_offerte_commerciali_utilities_offerta_id | offerta_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_offerte_commerciali_utilities | `CREATE UNIQUE INDEX pk_offerte_commerciali_utilities ON vendite.offerte_commerciali_utilities USING btree (id)` |
| uq_offerte_commerciali_utilities_offerta_id | `CREATE UNIQUE INDEX uq_offerte_commerciali_utilities_offerta_id ON vendite.offerte_commerciali_utilities USING btree (offerta_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_offerte_commerciali_utilities_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_offerte_commerciali_utilities_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_offerte_commerciali_utilities_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_offerte_commerciali_utilities_a10_guard_coppia_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_fornitura_guard_coppia('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_utilities_a10_guard_coppia_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_fornitura_guard_coppia('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_utilities_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_utilities_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_offerte_commerciali_utilities_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
