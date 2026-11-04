{% include-markdown "it/dbzero/pagamenti/manual/enti_incasso.md" %}
# 📚 Tabella `enti_incasso`

> 📝 **Descrizione**
>
> Canali di provenienza flussi incasso (banca, poste, psp, altro)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | text | NO |  |
| codice_interno | text | YES |  |
| descrizione | text | NO |  |
| tipo | text | NO |  |
| attivo | boolean | NO | true |
| centro_riscossione_id | bigint | YES |  |
| soggetto_ruolo_id | bigint | YES |  |
| bank_branch_id | bigint | YES |  |
| formato_flusso | text | YES |  |
| regole_match | jsonb | NO | '{}'::jsonb |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| soggetto_ruolo_conto_bancario_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_enti_incasso_bank_branch_tipo |  |
| CHECK | chk_enti_incasso_tipo |  |
| FOREIGN KEY | fk_enti_incasso_bank_branch | bank_branch_id |
| FOREIGN KEY | fk_enti_incasso_centro_riscossione | centro_riscossione_id |
| FOREIGN KEY | fk_enti_incasso_conto_incasso | soggetto_ruolo_conto_bancario_id |
| FOREIGN KEY | fk_enti_incasso_soggetto_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_enti_incasso | id |
| UNIQUE | uq_enti_incasso_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_enti_incasso | `CREATE UNIQUE INDEX pk_enti_incasso ON pagamenti.enti_incasso USING btree (id)` |
| uq_enti_incasso_codice | `CREATE UNIQUE INDEX uq_enti_incasso_codice ON pagamenti.enti_incasso USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_enti_incasso_a10_bank_branches_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'bank_branches', 'attivo', 'bank_branch_id', 'id')` |
| trg_enti_incasso_a10_bank_branches_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'bank_branches', 'attivo', 'bank_branch_id', 'id')` |
| trg_enti_incasso_a10_centri_riscossione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id', 'id')` |
| trg_enti_incasso_a10_centri_riscossione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id', 'id')` |
| trg_enti_incasso_a10_guard_conto_incasso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_enti_incasso_guard_conto_incasso()` |
| trg_enti_incasso_a10_guard_conto_incasso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_enti_incasso_guard_conto_incasso()` |
| trg_enti_incasso_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_enti_incasso_a10_vendite_contabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_contabili', 'ente_incasso_id', 'id', 'attivo')` |
| trg_enti_incasso_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_enti_incasso_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_enti_incasso_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_enti_incasso_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_enti_incasso_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_enti_incasso_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_enti_incasso_guard_psp_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_enti_incasso_guard_psp()` |
| trg_enti_incasso_guard_psp_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_enti_incasso_guard_psp()` |

---
{% include-markdown "signature-core.md" %}
