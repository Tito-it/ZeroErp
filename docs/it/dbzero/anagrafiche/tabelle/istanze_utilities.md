{% include-markdown "it/dbzero/anagrafiche/manual/istanze_utilities.md" %}
# 📚 Tabella `istanze_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.istanze_utilities_id_seq'::regclass) |
| fittizia | boolean | NO | false |
| codice | character varying | NO |  |
| proprietario_inquilino | character | NO | 'I'::bpchar |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| soggetto_id | uuid | NO |  |
| indirizzo_dettaglio_id | integer | NO |  |
| tx_id | uuid | YES |  |
| parent_istanza_id | integer | NO |  |
| pdp_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_istanza_fittizia_indirizzo |  |
| CHECK | chk_istanze_utilities_prop_inquilino |  |
| CHECK | chk_iu_pdp_requires_address |  |
| FOREIGN KEY | fk_istanze_utilities_indirizzo_dettaglio | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_istanze_utilities_parent_istanza | parent_istanza_id |
| FOREIGN KEY | fk_istanze_utilities_soggetto | soggetto_id |
| FOREIGN KEY | fk_iu_pdp_id_addr | pdp_id, indirizzo_dettaglio_id |
| PRIMARY KEY | pk_istanze_utilities | id |
| UNIQUE | uq_istanze_utilities_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| idx_iu_pdp_id_addr | `CREATE INDEX idx_iu_pdp_id_addr ON anagrafiche.istanze_utilities USING btree (pdp_id, indirizzo_dettaglio_id)` |
| ix_istanze_utilities_indirizzo_dettaglio_id | `CREATE INDEX ix_istanze_utilities_indirizzo_dettaglio_id ON anagrafiche.istanze_utilities USING btree (indirizzo_dettaglio_id)` |
| ix_istanze_utilities_soggetto_id | `CREATE INDEX ix_istanze_utilities_soggetto_id ON anagrafiche.istanze_utilities USING btree (soggetto_id)` |
| pk_istanze_utilities | `CREATE UNIQUE INDEX pk_istanze_utilities ON anagrafiche.istanze_utilities USING btree (id)` |
| uq_istanze_utilities_codice | `CREATE UNIQUE INDEX uq_istanze_utilities_codice ON anagrafiche.istanze_utilities USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_istanze_utilities_ins_upd_clean_fields | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_ins_upd_clean_fields()` |
| trg_istanze_utilities_ins_upd_clean_fields | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_ins_upd_clean_fields()` |
| trg_istanze_utilities_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_utilities_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_istanze_utilities_upd_protect_codice | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_upd_protect_codice()` |
| trg_upd_istanze_utilities_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
