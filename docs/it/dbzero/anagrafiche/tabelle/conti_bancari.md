{% include-markdown "it/dbzero/anagrafiche/manual/conti_bancari.md" %}
# 📚 Tabella `conti_bancari`

> 📝 **Descrizione**
>
> Anagrafe unica dei conti_bancari (IBAN), deduplicata a livello globale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| iban | character varying | NO |  |
| bic_swift | character varying | YES |  |
| intestatario_predefinito | character varying | YES |  |
| paese | character | YES |  |
| attivo | boolean | NO | true |
| verificato | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| bank_branch_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_conti_bancari_bic_fmt |  |
| CHECK | chk_conti_bancari_iban_fmt |  |
| CHECK | chk_conti_bancari_paese_fmt |  |
| FOREIGN KEY | fk_conti_bancari_bank_branches | bank_branch_id |
| PRIMARY KEY | pk_conti_bancari | id |
| UNIQUE | uq_conti_bancari_iban | iban |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_conti_bancari_attivo | `CREATE INDEX ix_conti_bancari_attivo ON anagrafiche.conti_bancari USING btree (attivo)` |
| pk_conti_bancari | `CREATE UNIQUE INDEX pk_conti_bancari ON anagrafiche.conti_bancari USING btree (id)` |
| uq_conti_bancari_iban | `CREATE UNIQUE INDEX uq_conti_bancari_iban ON anagrafiche.conti_bancari USING btree (iban)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_conti_bancari_a10_bank_branches_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'bank_branches', 'attivo', 'bank_branch_id', 'id')` |
| trg_conti_bancari_a10_bank_branches_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'bank_branches', 'attivo', 'bank_branch_id', 'id')` |
| trg_conti_bancari_a10_soggetti_conti_bancari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_conti_bancari', 'conto_bancario_id', 'id', 'attivo')` |
| trg_conti_bancari_a10_soggetti_ruoli_conti_bancari_block_b38964 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_ruoli_conti_bancari', 'conto_bancario_id', 'id', 'attivo')` |
| trg_conti_bancari_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_conti_bancari_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_conti_bancari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_conti_bancari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_conti_bancari_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_conti_bancari_normalize()` |
| trg_conti_bancari_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_conti_bancari_normalize()` |
| trg_conti_bancari_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('conti_bancari_id')` |
| trg_conti_bancari_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('conti_bancari_id')` |

---
{% include-markdown "signature-core.md" %}
