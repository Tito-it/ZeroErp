{% include-markdown "it/dbzero/vendite/manual/contratti_utilities.md" %}
# 📚 Tabella `contratti_utilities`

> 📝 **Descrizione**
>
> Snapshot precontrattuali per contratti utilities (1:1 con vendite.contratti).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| contratto_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| istanza_dati_precontrattuali_id | bigint | YES |  |
| classe_utenza_id | integer | YES |  |
| param_1_num | numeric | YES |  |
| param_2_txt | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tipo_utenza_id | integer | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_contratti_utilities_param_1_num_finito |  |
| FOREIGN KEY | fk_contratti_utilities_classi_utenze | classe_utenza_id |
| FOREIGN KEY | fk_contratti_utilities_contratti | contratto_id |
| FOREIGN KEY | fk_contratti_utilities_istanze_dati_precontrattuali | istanza_dati_precontrattuali_id |
| FOREIGN KEY | fk_contratti_utilities_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_contratti_utilities_tipo_utenza | tipo_utenza_id |
| FOREIGN KEY | fk_contratti_utilities_utilities | utility_id |
| PRIMARY KEY | pk_contratti_utilities | id |
| UNIQUE | uq_contratti_utilities_contratto_id | contratto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_contratti_utilities | `CREATE UNIQUE INDEX pk_contratti_utilities ON vendite.contratti_utilities USING btree (id)` |
| uq_contratti_utilities_contratto_id | `CREATE UNIQUE INDEX uq_contratti_utilities_contratto_id ON vendite.contratti_utilities USING btree (contratto_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contratti_utilities_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'contratto_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_contratti_utilities_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'contratto_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_contratti_utilities_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'contratto_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_contratti_utilities_a10_guard_coppia_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_fornitura_guard_coppia('CONTRATTO')` |
| trg_contratti_utilities_a10_guard_coppia_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_fornitura_guard_coppia('CONTRATTO')` |
| trg_contratti_utilities_a10_guard_tipo_classe_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_utilities_guard_tipo_classe()` |
| trg_contratti_utilities_a10_guard_tipo_classe_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_utilities_guard_tipo_classe()` |
| trg_contratti_utilities_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_utilities_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contratti_utilities_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
