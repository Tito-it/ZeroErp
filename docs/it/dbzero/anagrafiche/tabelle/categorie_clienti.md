{% include-markdown "it/dbzero/anagrafiche/manual/categorie_clienti.md" %}
# 📚 Tabella `categorie_clienti`

> 📝 **Descrizione**
>
> Categorie commerciali cliente con flag partecipazione promo e ordinamento UI.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(255) | NO |  |
| partecipa_promo | boolean | NO | true |
| ordinamento | smallint | NO | 100 |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| codice_interno | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_categorie_clienti_codice_interno_nonvuoto |  |
| PRIMARY KEY | pk_categorie_clienti | id |
| UNIQUE | uq_categorie_clienti_codice | codice |
| UNIQUE | uq_categorie_clienti_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_categorie_clienti_attivo | `CREATE INDEX ix_categorie_clienti_attivo ON anagrafiche.categorie_clienti USING btree (attivo)` |
| pk_categorie_clienti | `CREATE UNIQUE INDEX pk_categorie_clienti ON anagrafiche.categorie_clienti USING btree (id)` |
| uq_categorie_clienti_codice | `CREATE UNIQUE INDEX uq_categorie_clienti_codice ON anagrafiche.categorie_clienti USING btree (codice)` |
| uq_categorie_clienti_codice_interno | `CREATE UNIQUE INDEX uq_categorie_clienti_codice_interno ON anagrafiche.categorie_clienti USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_categorie_clienti_a10_billing_account_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'billing_account', 'categoria_cliente_id', 'id', 'attivo')` |
| trg_categorie_clienti_a10_categorie_clienti_listini_bloc_a0b560 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'categorie_clienti_listini', 'categoria_cliente_id', 'id', 'attivo')` |
| trg_categorie_clienti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_categorie_clienti_a10_parameter_overrides_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'parameter_overrides', 'categoria_cliente_id', 'id', 'attivo')` |
| trg_categorie_clienti_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_categorie_clienti_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_categorie_clienti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_categorie_clienti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_categorie_clienti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_categorie_clienti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
