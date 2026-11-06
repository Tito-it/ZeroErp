{% include-markdown "it/dbzero/vendite/manual/commesse_sorgenti.md" %}
# 📚 Tabella `commesse_sorgenti`

> 📝 **Descrizione**
>
> Link sorgente ROOT della commessa.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| commessa_id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | text | NO |  |
| sorgente_riga | bigint | YES |  |
| ruolo_link | character varying(16) | NO | 'ROOT'::character varying |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_commesse_sorgenti_ruolo |  |
| FOREIGN KEY | fk_commesse_sorgenti_commessa | commessa_id |
| FOREIGN KEY | fk_commesse_sorgenti_tipo | sorgente_tipo_id |
| PRIMARY KEY | pk_commesse_sorgenti | id |
| UNIQUE | uq_commesse_sorgenti_src_uid_commessa | sorgente_tipo_id, sorgente_uid, commessa_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_sorgenti_commessa | `CREATE INDEX ix_commesse_sorgenti_commessa ON vendite.commesse_sorgenti USING btree (commessa_id)` |
| pk_commesse_sorgenti | `CREATE UNIQUE INDEX pk_commesse_sorgenti ON vendite.commesse_sorgenti USING btree (id)` |
| uq_commesse_sorgenti_commessa_root | `CREATE UNIQUE INDEX uq_commesse_sorgenti_commessa_root ON vendite.commesse_sorgenti USING btree (commessa_id) WHERE ((ruolo_link)::text = 'ROOT'::text)` |
| uq_commesse_sorgenti_src_uid_commessa | `CREATE UNIQUE INDEX uq_commesse_sorgenti_src_uid_commessa ON vendite.commesse_sorgenti USING btree (sorgente_tipo_id, sorgente_uid, commessa_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_sorgenti_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_testuale()` |
| trg_commesse_sorgenti_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_testuale()` |
| trg_commesse_sorgenti_a10_guard_sorgente_omogeneita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_commesse_sorgenti_guard_emittente()` |
| trg_commesse_sorgenti_a10_guard_sorgente_omogeneita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_commesse_sorgenti_guard_emittente()` |
| trg_commesse_sorgenti_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_commesse_sorgenti_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_commesse_sorgenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_sorgenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_sorgenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_sorgenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_sorgenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_sorgenti_id')` |
| trg_commesse_sorgenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('commesse_sorgenti_id')` |

---
{% include-markdown "signature-core.md" %}
