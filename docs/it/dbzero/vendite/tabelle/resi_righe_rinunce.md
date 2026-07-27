{% include-markdown "it/dbzero/vendite/manual/resi_righe_rinunce.md" %}
# 📚 Tabella `resi_righe_rinunce`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| resi_riga_id | bigint | NO |  |
| qta | numeric | NO |  |
| note | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | k_resi_rinunce_qta_pos |  |
| FOREIGN KEY | fk_resi_rinunce_resi_riga | resi_riga_id |
| PRIMARY KEY | pk_resi_rinunce | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_rinunce_resi_riga_id | `CREATE INDEX ix_resi_rinunce_resi_riga_id ON vendite.resi_righe_rinunce USING btree (resi_riga_id)` |
| pk_resi_rinunce | `CREATE UNIQUE INDEX pk_resi_rinunce ON vendite.resi_righe_rinunce USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_rinunce_a10_resi_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_rinunce_a10_resi_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_rinunce_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_rinunce_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_rinunce_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_rinunce_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_rinunce_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_rinunce_guard()` |
| trg_resi_rinunce_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_rinunce_guard()` |

---
{% include-markdown "signature-core.md" %}
