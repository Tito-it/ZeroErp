{% include-markdown "it/dbzero/anagrafiche/manual/indirizzi_dettaglio.md" %}
# 📚 Tabella `indirizzi_dettaglio`

> 📝 **Descrizione**
>
> Dettaglio degli indirizzi, collegate allo stradario

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stradario_id | integer | NO |  |
| civico | integer | YES |  |
| estensione_civico | character varying(10) | YES |  |
| palazzina | character varying(50) | YES |  |
| interno | character varying(10) | YES |  |
| piano | character varying(10) | YES |  |
| civic_geoloc | geometry(Point,4326) | YES |  |
| altro | text | YES |  |
| via_norm | text | NO |  |
| civico_norm | text | NO |  |
| street_geoloc | geometry(Point,4326) | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| scala | character varying(10) | YES |  |
| indirizzo_normalizzato | text | YES |  |
| tx_id | uuid | YES |  |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_indirizzi_dettaglio_civico_positivo |  |
| CHECK | chk_indirizzi_dettaglio_dettaglio_leggibile |  |
| FOREIGN KEY | fk_stradario_config | stradario_id |
| PRIMARY KEY | pk_indirizzi_dettaglio | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_indirizzi_dettaglio_civic_geoloc_gist | `CREATE INDEX ix_indirizzi_dettaglio_civic_geoloc_gist ON anagrafiche.indirizzi_dettaglio USING gist (civic_geoloc)` |
| ix_indirizzi_dettaglio_indirizzo_norm_gin | `CREATE INDEX ix_indirizzi_dettaglio_indirizzo_norm_gin ON anagrafiche.indirizzi_dettaglio USING gin (indirizzo_normalizzato gin_trgm_ops)` |
| pk_indirizzi_dettaglio | `CREATE UNIQUE INDEX pk_indirizzi_dettaglio ON anagrafiche.indirizzi_dettaglio USING btree (id)` |
| uq_indirizzi_dettaglio_norm_v2 | `CREATE UNIQUE INDEX uq_indirizzi_dettaglio_norm_v2 ON anagrafiche.indirizzi_dettaglio USING btree (stradario_id, civico, estensione_civico, palazzina, scala, piano, interno) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_indirizzi_dettaglio_a10_catasto_unita_immobiliari_in_25baf0 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'catasto_unita_immobiliari_indirizzi', 'indirizzo_dettaglio_id', 'id', 'attivo')` |
| trg_indirizzi_dettaglio_a10_indirizzi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'indirizzi', 'indirizzo_dettaglio_id', 'id', 'attivo')` |
| trg_indirizzi_dettaglio_a10_indirizzi_soggetti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'indirizzi_soggetti', 'indirizzo_dettaglio_id', 'id', 'attivo')` |
| trg_indirizzi_dettaglio_a10_istanze_utilities_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'istanze_utilities', 'indirizzo_dettaglio_id', 'id', 'attivo')` |
| trg_indirizzi_dettaglio_a10_magazzini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'magazzini', 'indirizzo_dettaglio_id', 'id', 'attivo')` |
| trg_indirizzi_dettaglio_a10_pdp_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'pdp', 'indirizzo_dettaglio_id', 'id', 'attivo')` |
| trg_indirizzi_dettaglio_a10_protect_update_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_protect_update()` |
| trg_indirizzi_dettaglio_a10_via_non_soppressa_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('config', 'stradario', 'obsoleto_dal', 'stradario_id', 'id')` |
| trg_indirizzi_dettaglio_a10_via_non_soppressa_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('config', 'stradario', 'obsoleto_dal', 'stradario_id', 'id')` |
| trg_indirizzi_dettaglio_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_indirizzi_dettaglio_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_indirizzi_dettaglio_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_dettaglio_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_dettaglio_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()` |
| trg_indirizzi_dettaglio_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()` |
| trg_indirizzi_dettaglio_z10_guard_chiave_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave()` |
| trg_indirizzi_dettaglio_z10_guard_chiave_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave()` |
| trg_indirizzi_dettaglio_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzi_dettaglio_id')` |
| trg_indirizzi_dettaglio_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzi_dettaglio_id')` |

---
{% include-markdown "signature-core.md" %}
