{% include-markdown "it/dbzero/vendite/manual/ordini_righe_fulfillment.md" %}
# 📚 Tabella `ordini_righe_fulfillment`

> 📝 **Descrizione**
>
> Fulfillment parziale/totale da righe ordine a righe DDT (vendita).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_riga_id | bigint | NO |  |
| ddt_riga_id | bigint | NO |  |
| qta_evasa | numeric(18,6) | NO |  |
| note | character varying(200) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_r_ful_v_qta_pos |  |
| CHECK | chk_ordini_righe_fulfillment_qta_evasa_finito |  |
| FOREIGN KEY | fk_ordini_r_ful_v_ddt_riga | ddt_riga_id |
| FOREIGN KEY | fk_ordini_r_ful_v_ordine_riga | ordine_riga_id |
| PRIMARY KEY | pk_fulv | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_ordini_righe_fulfillment_ddt_riga_id | `CREATE INDEX ix_vendite_ordini_righe_fulfillment_ddt_riga_id ON vendite.ordini_righe_fulfillment USING btree (ddt_riga_id)` |
| pk_fulv | `CREATE UNIQUE INDEX pk_fulv ON vendite.ordini_righe_fulfillment USING btree (id)` |
| uq_ordini_r_ful_v_pair | `CREATE UNIQUE INDEX uq_ordini_r_ful_v_pair ON vendite.ordini_righe_fulfillment USING btree (ordine_riga_id, ddt_riga_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_righe_fulfillment_a05_doc_bozza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_riga_id', 'DRAFT', 'RIGA')` |
| trg_ordini_righe_fulfillment_a05_doc_bozza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_riga_id', 'DRAFT', 'RIGA')` |
| trg_ordini_righe_fulfillment_a05_guard_legame_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_riga_legame_guard('qta_evasa', 'ordine_riga_id')` |
| trg_ordini_righe_fulfillment_a05_guard_legame_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_ddt_riga_legame_guard('qta_evasa', 'ordine_riga_id')` |
| trg_ordini_righe_fulfillment_a10_ddt_righe_require_attiv_ae2869 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_ordini_righe_fulfillment_a10_ddt_righe_require_attiv_ae2869 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_ordini_righe_fulfillment_a10_guard_consistenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_ful_guard_consistenza()` |
| trg_ordini_righe_fulfillment_a10_guard_consistenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_ful_guard_consistenza()` |
| trg_ordini_righe_fulfillment_a10_ordini_righe_require_at_925d38 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ordini_righe', 'attivo', 'ordine_riga_id', 'id')` |
| trg_ordini_righe_fulfillment_a10_ordini_righe_require_at_925d38 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ordini_righe', 'attivo', 'ordine_riga_id', 'id')` |
| trg_ordini_righe_fulfillment_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_fulfillment_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_fulfillment_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_fulfillment_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_fulfillment_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_righe_fulfillment_id')` |
| trg_ordini_righe_fulfillment_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_righe_fulfillment_id')` |

---
{% include-markdown "signature-core.md" %}
