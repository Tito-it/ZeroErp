{% include-markdown "it/dbzero/anagrafiche/manual/bank_branches.md" %}
# 📚 Tabella `bank_branches`

> 📝 **Descrizione**
>
> Filiali di istituti di credito / bank branches collegate a soggetti_ruoli (ISTITUTO_CREDITO).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| bank_code | character varying(16) | NO |  |
| branch_code | character varying(16) | NO |  |
| bic_swift | character varying(11) | YES |  |
| name | character varying(255) | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | check_bank_branches_bic_swift_fmt |  |
| FOREIGN KEY | fk_bank_branches_soggetti_ruoli | soggetto_ruolo_id |
| PRIMARY KEY | pk_bank_branches | id |
| UNIQUE | uq_bank_branches_soggetto_ruolo_bank_branch_code | soggetto_ruolo_id, bank_code, branch_code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_bank_branches_attivo | `CREATE INDEX ix_bank_branches_attivo ON anagrafiche.bank_branches USING btree (attivo)` |
| ix_bank_branches_bank_code_trgm | `CREATE INDEX ix_bank_branches_bank_code_trgm ON anagrafiche.bank_branches USING gin (bank_code gin_trgm_ops)` |
| pk_bank_branches | `CREATE UNIQUE INDEX pk_bank_branches ON anagrafiche.bank_branches USING btree (id)` |
| uq_bank_branches_soggetto_ruolo_bank_branch_code | `CREATE UNIQUE INDEX uq_bank_branches_soggetto_ruolo_bank_branch_code ON anagrafiche.bank_branches USING btree (soggetto_ruolo_id, bank_code, branch_code)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_bank_branches_a10_conti_bancari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'conti_bancari', 'bank_branch_id', 'id', 'attivo')` |
| trg_bank_branches_a10_delete_block_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| trg_bank_branches_a10_enti_incasso_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'enti_incasso', 'bank_branch_id', 'id', 'attivo')` |
| trg_bank_branches_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_bank_branches_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_bank_branches_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_bank_branches_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_bank_branches_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('bank_branches_id')` |
| trg_bank_branches_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('bank_branches_id')` |
| trg_bank_guard_ruolo_bank_branches_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_bank_guard_ruolo_bank_branches()` |
| trg_bank_guard_ruolo_bank_branches_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_bank_guard_ruolo_bank_branches()` |

---
{% include-markdown "signature-core.md" %}
