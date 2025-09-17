{% include-markdown "it/dbzero/anagrafiche/manual/pdp.md" %}
# 📚 Tabella `pdp`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pdp | character varying | NO |  |
| utilities_id | bigint | NO |  |
| indirizzo_dettaglio_id | bigint | NO |  |
| cliente_id | bigint | YES |  |
| tx_id | uuid | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| user_insert | character varying | NO |  |
| user_update | character varying | NO |  |
| storicizza | boolean | NO | true |
| extra_info | jsonb | NO | '{}'::jsonb |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_pdp_codice_len |  |
| FOREIGN KEY | fk_pdp_clienti | cliente_id |
| FOREIGN KEY | fk_pdp_indirizzi_dettaglio | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_pdp_utilities | utilities_id |
| PRIMARY KEY | pk_pdp | id |
| UNIQUE | uq_pdp_addr_utility | utilities_id, indirizzo_dettaglio_id |
| UNIQUE | uq_pdp_codice | pdp |
| UNIQUE | uq_pdp_id_addr | indirizzo_dettaglio_id, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pdp_cliente_id | `CREATE INDEX ix_pdp_cliente_id ON anagrafiche.pdp USING btree (cliente_id)` |
| ix_pdp_indirizzo_dettaglio_id | `CREATE INDEX ix_pdp_indirizzo_dettaglio_id ON anagrafiche.pdp USING btree (indirizzo_dettaglio_id)` |
| ix_pdp_utilities_id | `CREATE INDEX ix_pdp_utilities_id ON anagrafiche.pdp USING btree (utilities_id)` |
| pk_pdp | `CREATE UNIQUE INDEX pk_pdp ON anagrafiche.pdp USING btree (id)` |
| uq_pdp_addr_utility | `CREATE UNIQUE INDEX uq_pdp_addr_utility ON anagrafiche.pdp USING btree (indirizzo_dettaglio_id, utilities_id)` |
| uq_pdp_codice | `CREATE UNIQUE INDEX uq_pdp_codice ON anagrafiche.pdp USING btree (pdp)` |
| uq_pdp_id_addr | `CREATE UNIQUE INDEX uq_pdp_id_addr ON anagrafiche.pdp USING btree (id, indirizzo_dettaglio_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pdp_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pdp_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pdp_upd_protect_cols | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_pdp_protect_cols()` |
| trg_z90_pdp_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('pdp_id')` |
| trg_z90_pdp_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('pdp_id')` |

---
{% include-markdown "signature-core.md" %}
