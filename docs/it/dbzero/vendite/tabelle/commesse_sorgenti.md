{% include-markdown "it/dbzero/vendite/manual/commesse_sorgenti.md" %}
# 📚 Tabella `commesse_sorgenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| commessa_id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | text | NO |  |
| sorgente_riga | bigint | YES |  |
| ruolo_link | character varying | NO | 'ROOT'::character varying |
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
| CHECK | chk_commesse_sorgenti_ruolo |  |
| FOREIGN KEY | fk_commesse_sorgenti_commessa | commessa_id |
| FOREIGN KEY | fk_commesse_sorgenti_tipo | sorgente_tipo_id |
| PRIMARY KEY | pk_commesse_sorgenti | id |
| UNIQUE | uq_commesse_sorgenti_commessa_ruolo | commessa_id, ruolo_link |
| UNIQUE | uq_commesse_sorgenti_src_uid_ruolo | sorgente_tipo_id, sorgente_uid, ruolo_link |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_sorgenti_commessa | `CREATE INDEX ix_commesse_sorgenti_commessa ON vendite.commesse_sorgenti USING btree (commessa_id)` |
| pk_commesse_sorgenti | `CREATE UNIQUE INDEX pk_commesse_sorgenti ON vendite.commesse_sorgenti USING btree (id)` |
| uq_commesse_sorgenti_commessa_ruolo | `CREATE UNIQUE INDEX uq_commesse_sorgenti_commessa_ruolo ON vendite.commesse_sorgenti USING btree (commessa_id, ruolo_link)` |
| uq_commesse_sorgenti_src_uid_ruolo | `CREATE UNIQUE INDEX uq_commesse_sorgenti_src_uid_ruolo ON vendite.commesse_sorgenti USING btree (sorgente_tipo_id, sorgente_uid, ruolo_link)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_sorgenti_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_commesse_sorgenti_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_commesse_sorgenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_sorgenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_sorgenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_sorgenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_sorgenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_sorgenti_id')` |
| trg_commesse_sorgenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_sorgenti_id')` |

---
{% include-markdown "signature-core.md" %}
