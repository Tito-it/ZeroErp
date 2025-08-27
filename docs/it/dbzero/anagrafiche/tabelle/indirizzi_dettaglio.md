{% include-markdown "it/dbzero/anagrafiche/manual/indirizzi_dettaglio.md" %}
# 📚 Tabella `indirizzi_dettaglio`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.indirizzi_dettaglio_id_seq'::regclass) |
| stradario_id | integer | NO |  |
| civico | integer | YES |  |
| estensione_civico | character varying | YES |  |
| palazzina | character varying | YES |  |
| interno | character varying | YES |  |
| piano | character varying | YES |  |
| civic_geoloc | USER-DEFINED | YES |  |
| altro | text | YES |  |
| via_norm | text | NO |  |
| civico_norm | text | NO |  |
| street_geoloc | USER-DEFINED | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| scala | character varying | YES |  |
| indirizzo_normalizzato | text | YES |  |
| tx_id | uuid | YES |  |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_stradario_config | stradario_id |
| PRIMARY KEY | pk_indirizzi_dettaglio | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_indirizzi_dettaglio_civic_geoloc_gist | `CREATE INDEX ix_indirizzi_dettaglio_civic_geoloc_gist ON anagrafiche.indirizzi_dettaglio USING gist (civic_geoloc)` |
| ix_indirizzi_dettaglio_stradario_id | `CREATE INDEX ix_indirizzi_dettaglio_stradario_id ON anagrafiche.indirizzi_dettaglio USING btree (stradario_id)` |
| ix_uq_indirizzi_dettaglio_norm | `CREATE UNIQUE INDEX ix_uq_indirizzi_dettaglio_norm ON anagrafiche.indirizzi_dettaglio USING btree (via_norm, civico_norm, interno, piano, palazzina)` |
| pk_indirizzi_dettaglio | `CREATE UNIQUE INDEX pk_indirizzi_dettaglio ON anagrafiche.indirizzi_dettaglio USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_block_deact_indirizzi_dettaglio__istanze_utilities | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'istanze_utilities', 'indirizzo_dettaglio_id')` |
| trg_block_deact_indirizzi_dettaglio__pdp | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'pdp', 'indirizzo_dettaglio_id')` |
| trg_indirizzi_dettaglio_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_dettaglio_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio()` |
| trg_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio()` |
| trg_upd_indirizzi_dettaglio_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_indirizzi_dettaglio_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('indirizzo_dettaglio_id')` |
| trg_z90_indirizzi_dettaglio_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('indirizzo_dettaglio_id')` |

---
{% include-markdown "signature-core.md" %}
