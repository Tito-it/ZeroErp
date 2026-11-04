{% include-markdown "it/dbzero/magazzino/manual/magazzini.md" %}
# 📚 Tabella `magazzini`

> 📝 **Descrizione**
>
> Anagrafica dei magazzini/depositi di un emittente fiscale (emittente_fiscale_id, l'ancora del perimetro RLS del dominio). Indirizzo legato a anagrafiche.indirizzi_dettaglio (un magazzino non e' un ruolo). Nessuna operazione di magazzino attraversa due emittenti (trasferimenti: guard stesso emittente).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | NO |  |
| indirizzo_dettaglio_id | bigint | NO |  |
| attivo | boolean | NO | true |
| predefinito | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| emittente_fiscale_id | bigint | NO |  |
| usa_ubicazioni | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_magazzini_codice_nonvuoto |  |
| FOREIGN KEY | fk_magazzini_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_magazzini_indirizzo_dettaglio | indirizzo_dettaglio_id |
| PRIMARY KEY | pk_magazzini | id |
| UNIQUE | uq_magazzini_codice | codice |
| UNIQUE | uq_magazzini_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_magazzini_indirizzo_dettaglio_id | `CREATE INDEX ix_magazzino_magazzini_indirizzo_dettaglio_id ON magazzino.magazzini USING btree (indirizzo_dettaglio_id)` |
| pk_magazzini | `CREATE UNIQUE INDEX pk_magazzini ON magazzino.magazzini USING btree (id)` |
| uq_mag_magazzini_predefinito_emittente | `CREATE UNIQUE INDEX uq_mag_magazzini_predefinito_emittente ON magazzino.magazzini USING btree (emittente_fiscale_id) WHERE predefinito` |
| uq_magazzini_codice | `CREATE UNIQUE INDEX uq_magazzini_codice ON magazzino.magazzini USING btree (codice)` |
| uq_magazzini_uid | `CREATE UNIQUE INDEX uq_magazzini_uid ON magazzino.magazzini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_magazzini_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_magazzini_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_magazzini_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_magazzini_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_magazzini_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_magazzini_a10_guard_usa_ubicazioni_upd | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_magazzini_guard_usa_ubicazioni()` |
| trg_magazzini_a10_indirizzi_dettaglio_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_magazzini_a10_indirizzi_dettaglio_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_magazzini_a10_inventari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE')` |
| trg_magazzini_a10_movimenti_attesi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti_attesi', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_resi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_rettifiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_ubicazioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'ubicazioni', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_valore_giacenza_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'valore_giacenza', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_magazzini_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_magazzini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_magazzini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_magazzini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_magazzini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_magazzini_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('magazzini_id')` |
| trg_magazzini_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('magazzini_id')` |

---
{% include-markdown "signature-core.md" %}
