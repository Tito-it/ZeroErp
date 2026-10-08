{% include-markdown "it/dbzero/magazzino/manual/assets.md" %}
# 📚 Tabella `assets`

> 📝 **Descrizione**
>
> Istanza fisica di un bene serializzato (contatore, apparecchiatura): l'oggetto che movimenti.asset_id sposta uno alla volta (|qta| = 1). Di un emittente (emittente_fiscale_id), con una proprieta' (ownership_id), eventualmente presso un billing account. Dal 2026-09-15 non porta piu' la posizione (magazzino, ubicazione): la dice il registro. Dal 2026-10-01 non porta il contratto: il registro non conosce i documenti che lo usano, e il legame, se servira', nasce nel contratto. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.7; brief-db-magazzino-registro-anello-interno (D-3).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| seriale | character varying(64) | NO |  |
| billing_account_id | bigint | YES |  |
| data_stato | timestamp with time zone | NO | now() |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | text | YES | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES | now() |
| storicizza | boolean | NO | false |
| stato_id | bigint | NO |  |
| ownership_id | bigint | NO |  |
| emittente_fiscale_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_assets_articolo | articolo_id |
| FOREIGN KEY | fk_mag_assets_billing_account | billing_account_id |
| FOREIGN KEY | fk_mag_assets_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_mag_assets_ownership_id | ownership_id |
| FOREIGN KEY | fk_mag_assets_stato | stato_id |
| PRIMARY KEY | pk_mag_assets | id |
| UNIQUE | uq_mag_assets_seriale | seriale |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_assets_articolo_id | `CREATE INDEX ix_magazzino_assets_articolo_id ON magazzino.assets USING btree (articolo_id)` |
| ix_magazzino_assets_ownership_id | `CREATE INDEX ix_magazzino_assets_ownership_id ON magazzino.assets USING btree (ownership_id)` |
| ix_magazzino_assets_stato_id | `CREATE INDEX ix_magazzino_assets_stato_id ON magazzino.assets USING btree (stato_id)` |
| pk_mag_assets | `CREATE UNIQUE INDEX pk_mag_assets ON magazzino.assets USING btree (id)` |
| uq_mag_assets_seriale | `CREATE UNIQUE INDEX uq_mag_assets_seriale ON magazzino.assets USING btree (seriale)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_assets_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_assets_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_assets_a10_assets_ownership_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'assets_ownership', 'attivo', 'ownership_id', 'id')` |
| trg_assets_a10_assets_ownership_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'assets_ownership', 'attivo', 'ownership_id', 'id')` |
| trg_assets_a10_ddt_righe_prelievi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_prelievi', 'asset_id', 'id', 'attivo')` |
| trg_assets_a10_default_emittente_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')` |
| trg_assets_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_assets_a10_emittenti_fiscali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_assets_a10_eventi_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'eventi_assets', 'asset_id', 'id', 'attivo')` |
| trg_assets_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_assets_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_assets_a10_inventari_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari_righe', 'asset_id', 'id', 'attivo')` |
| trg_assets_a10_movimenti_attesi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti_attesi', 'asset_id', 'id', 'attivo')` |
| trg_assets_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'asset_id', 'id', 'attivo')` |
| trg_assets_a10_note_asset_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'note_asset', 'target_id', 'id', 'attivo')` |
| trg_assets_a10_rettifiche_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche_righe', 'asset_id', 'id', 'attivo')` |
| trg_assets_a10_stati_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_assets', 'attivo', 'stato_id', 'id')` |
| trg_assets_a10_stati_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_assets', 'attivo', 'stato_id', 'id')` |
| trg_assets_a10_trasferimenti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'trasferimenti_righe', 'asset_id', 'id', 'attivo')` |
| trg_assets_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_assets_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_assets_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_assets_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_assets_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('assets_id')` |
| trg_assets_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('assets_id')` |

---
{% include-markdown "signature-core.md" %}
