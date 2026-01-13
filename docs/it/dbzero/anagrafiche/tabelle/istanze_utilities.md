{% include-markdown "it/dbzero/anagrafiche/manual/istanze_utilities.md" %}
# 📚 Tabella `istanze_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fittizia | boolean | NO | false |
| codice | character varying | NO |  |
| proprietario_inquilino | character | NO | 'I'::bpchar |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| soggetto_id | uuid | NO |  |
| indirizzo_dettaglio_id | bigint | YES |  |
| tx_id | uuid | YES |  |
| parent_istanza_id | bigint | YES |  |
| pdp_id | bigint | YES |  |
| catasto_unita_immobiliare_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_istanza_fittizia_indirizzo |  |
| CHECK | chk_istanze_utilities_prop_inquilino |  |
| CHECK | chk_iu_pdp_not_fittizia |  |
| CHECK | chk_iu_pdp_requires_address |  |
| FOREIGN KEY | fk_istanze_utilities_indirizzo_dettaglio | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_istanze_utilities_parent_istanza | parent_istanza_id |
| FOREIGN KEY | fk_istanze_utilities_soggetto | soggetto_id |
| FOREIGN KEY | fk_iu_catasto_unita_immobiliare | catasto_unita_immobiliare_id |
| FOREIGN KEY | fk_iu_pdp_id_addr | indirizzo_dettaglio_id, pdp_id |
| PRIMARY KEY | pk_istanze_utilities | id |
| UNIQUE | uq_istanze_utilities_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| idx_iu_pdp_id_addr | `CREATE INDEX idx_iu_pdp_id_addr ON anagrafiche.istanze_utilities USING btree (pdp_id, indirizzo_dettaglio_id)` |
| ix_istanze_utilities_soggetto_id | `CREATE INDEX ix_istanze_utilities_soggetto_id ON anagrafiche.istanze_utilities USING btree (soggetto_id)` |
| pk_istanze_utilities | `CREATE UNIQUE INDEX pk_istanze_utilities ON anagrafiche.istanze_utilities USING btree (id)` |
| uq_istanze_utilities_codice | `CREATE UNIQUE INDEX uq_istanze_utilities_codice ON anagrafiche.istanze_utilities USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_istanze_utilities_a10_indirizzi_dettaglio_require_at_222826 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id')` |
| trg_istanze_utilities_a10_indirizzi_dettaglio_require_at_222826 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id')` |
| trg_istanze_utilities_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')` |
| trg_istanze_utilities_a10_pdp_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'pdp', 'attivo', 'pdp_id')` |
| trg_istanze_utilities_a10_pdp_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'pdp', 'attivo', 'pdp_id')` |
| trg_istanze_utilities_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id')` |
| trg_istanze_utilities_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id')` |
| trg_istanze_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_istanze_utilities_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_utilities_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_utilities_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_normalize()` |
| trg_istanze_utilities_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_normalize()` |
| trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()` |
| trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()` |
| trg_iu_z50_clone_catasto_from_parent_aft_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_iu_clone_catasto_from_parent()` |

---
{% include-markdown "signature-core.md" %}
