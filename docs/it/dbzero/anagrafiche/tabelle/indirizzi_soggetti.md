{% include-markdown "it/dbzero/anagrafiche/manual/indirizzi_soggetti.md" %}
# 📚 Tabella `indirizzi_soggetti`

> 📝 **Descrizione**
>
> Indirizzi associati direttamente ai soggetti (non ai ruoli).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_id | uuid | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| indirizzo_dettaglio_id | bigint | YES |  |
| indirizzo_libero | text | YES |  |
| stato_id | integer | YES |  |
| administrative_area | character varying(100) | YES |  |
| locality | character varying(100) | YES |  |
| sublocality | character varying(100) | YES |  |
| postal_code | character varying(20) | YES |  |
| comune_id | integer | YES |  |
| codice_postale_id | integer | YES |  |
| geoloc | geometry(Point,4326) | YES |  |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_indirizzi_soggetti_free_requirements |  |
| CHECK | chk_indirizzi_soggetti_xor_norm_libero |  |
| FOREIGN KEY | fk_indirizzi_soggetti_codici_postali | codice_postale_id |
| FOREIGN KEY | fk_indirizzi_soggetti_comuni | comune_id |
| FOREIGN KEY | fk_indirizzi_soggetti_indirizzi_dettaglio | indirizzo_dettaglio_id |
| FOREIGN KEY | fk_indirizzi_soggetti_soggetti | soggetto_id |
| FOREIGN KEY | fk_indirizzi_soggetti_stati | stato_id |
| FOREIGN KEY | fk_indirizzi_soggetti_tipi_indirizzi | tipo_indirizzo_id |
| PRIMARY KEY | pk_indirizzi_soggetti | id |
| UNIQUE | uq_indirizzi_soggetti_soggetto_tipo | soggetto_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_indirizzi_soggetti_tipo_indirizzo_id | `CREATE INDEX ix_anagrafiche_indirizzi_soggetti_tipo_indirizzo_id ON anagrafiche.indirizzi_soggetti USING btree (tipo_indirizzo_id)` |
| pk_indirizzi_soggetti | `CREATE UNIQUE INDEX pk_indirizzi_soggetti ON anagrafiche.indirizzi_soggetti USING btree (id)` |
| uq_indirizzi_soggetti_soggetto_tipo | `CREATE UNIQUE INDEX uq_indirizzi_soggetti_soggetto_tipo ON anagrafiche.indirizzi_soggetti USING btree (soggetto_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_indirizzi_soggetti_a10_guard_tipo_indirizzo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo()` |
| trg_indirizzi_soggetti_a10_guard_tipo_indirizzo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo()` |
| trg_indirizzi_soggetti_a10_indirizzi_dettaglio_require_a_a86562 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_soggetti_a10_indirizzi_dettaglio_require_a_a86562 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_indirizzi_soggetti_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_indirizzi_soggetti_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_indirizzi_soggetti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_indirizzi_soggetti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_indirizzi_soggetti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_soggetti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_soggetti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_base_normalize()` |
| trg_indirizzi_soggetti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_base_normalize()` |
| trg_indirizzi_soggetti_sync_geoloc_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc()` |
| trg_indirizzi_soggetti_sync_geoloc_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc()` |
| trg_indirizzi_soggetti_z10_guard_forma_libera_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_guard_forma_libera()` |
| trg_indirizzi_soggetti_z10_guard_forma_libera_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_indirizzi_guard_forma_libera()` |
| trg_indirizzi_soggetti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzi_soggetti_id')` |
| trg_indirizzi_soggetti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('indirizzi_soggetti_id')` |

---
{% include-markdown "signature-core.md" %}
