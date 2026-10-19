{% include-markdown "it/dbzero/vendite/manual/resi_righe_riconsegne.md" %}
# 📚 Tabella `resi_righe_riconsegne`

> 📝 **Descrizione**
>
> Ponte riga-reso &lt;-&gt; riga-DDT di ri-spedizione (brief §4b, mirror ordini_righe_fulfillment). Supporta ri-consegna parziale/multipla; lo stato ri-consegna e derivato dalla copertura. rev 2026-07-13.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| resi_riga_id | bigint | NO |  |
| ddt_riga_id | bigint | NO |  |
| qta | numeric | NO |  |
| note | character varying(255) | YES |  |
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
| CHECK | chk_resi_righe_riconsegne_qta_finito |  |
| CHECK | k_resi_riconsegne_qta_pos |  |
| FOREIGN KEY | fk_resi_riconsegne_ddt_riga | ddt_riga_id |
| FOREIGN KEY | fk_resi_riconsegne_resi_riga | resi_riga_id |
| PRIMARY KEY | pk_resi_riconsegne | id |
| UNIQUE | uq_resi_riconsegne_pair | resi_riga_id, ddt_riga_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_righe_riconsegne_ddt_riga_id | `CREATE INDEX ix_resi_righe_riconsegne_ddt_riga_id ON vendite.resi_righe_riconsegne USING btree (ddt_riga_id)` |
| pk_resi_riconsegne | `CREATE UNIQUE INDEX pk_resi_riconsegne ON vendite.resi_righe_riconsegne USING btree (id)` |
| uq_resi_riconsegne_pair | `CREATE UNIQUE INDEX uq_resi_riconsegne_pair ON vendite.resi_righe_riconsegne USING btree (resi_riga_id, ddt_riga_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_riconsegne_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_riconsegne_guard()` |
| trg_resi_riconsegne_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_riconsegne_guard()` |
| trg_resi_righe_riconsegne_a05_doc_bozza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_riga_id', 'DRAFT', 'RIGA')` |
| trg_resi_righe_riconsegne_a05_doc_bozza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_riga_id', 'DRAFT', 'RIGA')` |
| trg_resi_righe_riconsegne_a05_guard_legame_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_riga_legame_guard('qta', 'resi_riga_id')` |
| trg_resi_righe_riconsegne_a05_guard_legame_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_ddt_riga_legame_guard('qta', 'resi_riga_id')` |
| trg_resi_righe_riconsegne_a10_ddt_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_resi_righe_riconsegne_a10_ddt_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'ddt_righe', 'attivo', 'ddt_riga_id', 'id')` |
| trg_resi_righe_riconsegne_a10_resi_righe_require_attivo__329762 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_riconsegne_a10_resi_righe_require_attivo__329762 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_riconsegne_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_riconsegne_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_riconsegne_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_riconsegne_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_riconsegne_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_riconsegne_id')` |
| trg_resi_righe_riconsegne_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_riconsegne_id')` |

---
{% include-markdown "signature-core.md" %}
