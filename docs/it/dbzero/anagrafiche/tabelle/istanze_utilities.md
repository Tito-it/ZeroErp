{% include-markdown "it/dbzero/anagrafiche/manual/istanze_utilities.md" %}
# 📚 Tabella `istanze_utilities`

> 📝 **Descrizione**
>
> Istanza di attivazione di una utility per un soggetto

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fittizia | boolean | NO | false |
| codice | character varying(30) | NO |  |
| proprietario_inquilino | character(1) | NO | 'I'::bpchar |
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
| FOREIGN KEY | fk_iu_pdp_id_addr | pdp_id, indirizzo_dettaglio_id |
| PRIMARY KEY | pk_istanze_utilities | id |
| UNIQUE | uq_istanze_utilities_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| idx_iu_pdp_id_addr | `CREATE INDEX idx_iu_pdp_id_addr ON anagrafiche.istanze_utilities USING btree (pdp_id, indirizzo_dettaglio_id)` |
| ix_anagrafiche_istanze_utilities_soggetto_id | `CREATE INDEX ix_anagrafiche_istanze_utilities_soggetto_id ON anagrafiche.istanze_utilities USING btree (soggetto_id)` |
| pk_istanze_utilities | `CREATE UNIQUE INDEX pk_istanze_utilities ON anagrafiche.istanze_utilities USING btree (id)` |
| uq_istanze_utilities_codice | `CREATE UNIQUE INDEX uq_istanze_utilities_codice ON anagrafiche.istanze_utilities USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_istanze_utilities_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_gen_codice()` |
| trg_istanze_utilities_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_gen_codice()` |
| trg_istanze_utilities_a10_indirizzi_dettaglio_require_at_222826 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_istanze_utilities_a10_indirizzi_dettaglio_require_at_222826 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_istanze_utilities_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE', 'soggetto_id', 'E_ISTANZA_SOGGETTO_IMMUTABILE')` |
| trg_istanze_utilities_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_istanze_utilities_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_istanze_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_istanze_utilities_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_istanze_utilities_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_utilities_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_utilities_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_normalize()` |
| trg_istanze_utilities_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_normalize()` |
| trg_istanze_utilities_z90_guard_clienti_chiave_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave()` |
| trg_istanze_utilities_z90_require_utility_dichiarata_ins | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata()` |
| trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()` |
| trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()` |
| trg_iu_z50_clone_catasto_from_parent_aft_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_iu_clone_catasto_from_parent()` |

---
{% include-markdown "signature-core.md" %}
