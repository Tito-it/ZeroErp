{% include-markdown "it/dbzero/anagrafiche/manual/conti_bancari.md" %}
# 📚 Tabella `conti_bancari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| iban | character varying | NO |  |
| bic_swift | character varying | YES |  |
| intestatario_predefinito | character varying | YES |  |
| paese | character | YES |  |
| banca_nome | character varying | YES |  |
| attivo | boolean | NO | true |
| verificato | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_conti_bancari_bic_fmt |  |
| CHECK | chk_conti_bancari_iban_fmt |  |
| CHECK | chk_conti_bancari_paese_fmt |  |
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
| trg_block_deact_conti_bancari_soggetti_conti_bancari | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_conti_bancari', 'conto_id')` |
| trg_block_deact_conti_bancari_soggetti_ruoli_conti_bancari | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'soggetti_ruoli_conti_bancari', 'conto_id')` |
| trg_conti_bancari_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_conti_bancari_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_conti_bancari_ins_upd_normalize | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_conti_bancari_ins_upd_normalize()` |
| trg_conti_bancari_ins_upd_normalize | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_conti_bancari_ins_upd_normalize()` |
| trg_upd_conti_bancari_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_conti_bancari_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('conti_bancari_id')` |
| trg_z90_conti_bancari_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('conti_bancari_id')` |

---
{% include-markdown "signature-core.md" %}
