# 📚 Tabella `magazzini`

> 📝 **Descrizione**
>
> Anagrafica magazzini/depositi. Indirizzo legato a anagrafiche.indirizzi_dettaglio (magazzino non è un ruolo).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| indirizzo_dettaglio_id | bigint | NO |  |
| attivo | boolean | NO | true |
| predefinito | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_magazzini_codice_nonvuoto |  |
| FOREIGN KEY | fk_magazzini_indirizzo_dettaglio | indirizzo_dettaglio_id |
| PRIMARY KEY | pk_magazzini | id |
| UNIQUE | uq_magazzini_codice | codice |
| UNIQUE | uq_magazzini_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_magazzini_indirizzo_dettaglio_id | `CREATE INDEX ix_magazzino_magazzini_indirizzo_dettaglio_id ON magazzino.magazzini USING btree (indirizzo_dettaglio_id)` |
| pk_magazzini | `CREATE UNIQUE INDEX pk_magazzini ON magazzino.magazzini USING btree (id)` |
| uq_magazzini_codice | `CREATE UNIQUE INDEX uq_magazzini_codice ON magazzino.magazzini USING btree (codice)` |
| uq_magazzini_uid | `CREATE UNIQUE INDEX uq_magazzini_uid ON magazzino.magazzini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_magazzini_a10_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'assets', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_costo_medio_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'costo_medio', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_indirizzi_dettaglio_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_magazzini_a10_indirizzi_dettaglio_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'indirizzi_dettaglio', 'attivo', 'indirizzo_dettaglio_id', 'id')` |
| trg_magazzini_a10_inventari_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')` |
| trg_magazzini_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_reservations_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'reservations', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_rettifiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_a10_ubicazioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'ubicazioni', 'magazzino_id', 'id', 'attivo')` |
| trg_magazzini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_magazzini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_magazzini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_magazzini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_magazzini_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_magazzini_normalize()` |
| trg_magazzini_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_magazzini_normalize()` |
| trg_magazzini_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('magazzini_id')` |
| trg_magazzini_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('magazzini_id')` |

---
{% include-markdown "signature-core.md" %}
