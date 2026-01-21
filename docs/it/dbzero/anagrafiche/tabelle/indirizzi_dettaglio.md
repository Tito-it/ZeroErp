{% include-markdown "it/dbzero/anagrafiche/manual/indirizzi_dettaglio.md" %}
# 📚 Tabella `indirizzi_dettaglio`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
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
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
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
| ix_anagrafiche_indirizzi_dettaglio_stradario_id | `CREATE INDEX ix_anagrafiche_indirizzi_dettaglio_stradario_id ON anagrafiche.indirizzi_dettaglio USING btree (stradario_id)` |
| ix_indirizzi_dettaglio_civic_geoloc_gist | `CREATE INDEX ix_indirizzi_dettaglio_civic_geoloc_gist ON anagrafiche.indirizzi_dettaglio USING gist (civic_geoloc)` |
| pk_indirizzi_dettaglio | `CREATE UNIQUE INDEX pk_indirizzi_dettaglio ON anagrafiche.indirizzi_dettaglio USING btree (id)` |
| uq_indirizzi_dettaglio_norm | `CREATE UNIQUE INDEX uq_indirizzi_dettaglio_norm ON anagrafiche.indirizzi_dettaglio USING btree (stradario_id, civico, COALESCE(estensione_civico, ''::character varying), COALESCE(palazzina, ''::character varying), COALESCE(scala, ''::character varying), COALESCE(piano, ''::character varying), COALESCE(interno, ''::character varying))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_indirizzi_dettaglio_a10_catasto_unita_immobiliari_in_25baf0 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'catasto_unita_immobiliari_indirizzi', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_dettaglio_a10_indirizzi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'indirizzi', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_dettaglio_a10_indirizzi_soggetti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'indirizzi_soggetti', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_dettaglio_a10_istanze_utilities_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'istanze_utilities', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_dettaglio_a10_magazzini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'magazzini', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_dettaglio_a10_pdp_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'pdp', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_dettaglio_a10_protect_update_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_protect_update()` |
| trg_indirizzi_dettaglio_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_indirizzi_dettaglio_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_dettaglio_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_dettaglio_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()` |
| trg_indirizzi_dettaglio_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()` |
| trg_indirizzi_dettaglio_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzi_dettaglio_id')` |
| trg_indirizzi_dettaglio_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzi_dettaglio_id')` |

---
{% include-markdown "signature-core.md" %}
