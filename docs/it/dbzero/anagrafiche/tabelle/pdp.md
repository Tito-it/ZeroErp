{% include-markdown "it/dbzero/anagrafiche/manual/pdp.md" %}
# 📚 Tabella `pdp`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pdp | character varying | NO |  |
| utility_id | bigint | NO |  |
| indirizzo_dettaglio_id | bigint | NO |  |
| cliente_id | bigint | YES |  |
| tx_id | uuid | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| stato_pdp_id | bigint | NO |  |
| attivo | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_pdp_codice_len |  |
| FOREIGN KEY | fk_pdp_clienti | cliente_id |
| FOREIGN KEY | fk_pdp_indirizzi_dettaglio | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_pdp_stati_pdp | stato_pdp_id |
| FOREIGN KEY | fk_pdp_utility | utility_id |
| PRIMARY KEY | pk_pdp | id |
| UNIQUE | uq_pdp_addr_utility | indirizzo_dettaglio_id, utility_id |
| UNIQUE | uq_pdp_codice | pdp |
| UNIQUE | uq_pdp_id_addr | id, indirizzo_dettaglio_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_pdp_cliente_id | `CREATE INDEX ix_anagrafiche_pdp_cliente_id ON anagrafiche.pdp USING btree (cliente_id)` |
| ix_anagrafiche_pdp_indirizzo_dettaglio_id | `CREATE INDEX ix_anagrafiche_pdp_indirizzo_dettaglio_id ON anagrafiche.pdp USING btree (indirizzo_dettaglio_id)` |
| ix_anagrafiche_pdp_utility_id | `CREATE INDEX ix_anagrafiche_pdp_utility_id ON anagrafiche.pdp USING btree (utility_id)` |
| pk_pdp | `CREATE UNIQUE INDEX pk_pdp ON anagrafiche.pdp USING btree (id)` |
| uq_pdp_addr_utility | `CREATE UNIQUE INDEX uq_pdp_addr_utility ON anagrafiche.pdp USING btree (indirizzo_dettaglio_id, utility_id)` |
| uq_pdp_codice | `CREATE UNIQUE INDEX uq_pdp_codice ON anagrafiche.pdp USING btree (pdp)` |
| uq_pdp_id_addr | `CREATE UNIQUE INDEX uq_pdp_id_addr ON anagrafiche.pdp USING btree (id, indirizzo_dettaglio_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pdp_a10_clienti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'clienti', 'pdp_id', 'id', 'attivo')` |
| trg_pdp_a10_guard_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_pdp_a10_guard()` |
| trg_pdp_a10_indirizzi_dettaglio_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_pdp_a10_indirizzi_dettaglio_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_pdp_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('pdp', 'CODICE_NON_MODIFICABILE')` |
| trg_pdp_a10_set_default_stato_ins | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_pdp_set_default_stato()` |
| trg_pdp_a10_stati_pdp_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_pdp', 'attivo', 'stato_pdp_id', 'id')` |
| trg_pdp_a10_stati_pdp_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_pdp', 'attivo', 'stato_pdp_id', 'id')` |
| trg_pdp_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_pdp_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_pdp_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pdp_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pdp_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('pdp_id')` |
| trg_pdp_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('pdp_id')` |

---
{% include-markdown "signature-core.md" %}
