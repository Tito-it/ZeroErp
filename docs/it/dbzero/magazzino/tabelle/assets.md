{% include-markdown "it/dbzero/magazzino/manual/assets.md" %}
# 📚 Tabella `assets`

> 📝 **Descrizione**
>
> Istanza fisica di bene durevole (contatore/PC/stampante ecc.) serializzato

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| seriale | character varying | NO |  |
| billing_account_id | bigint | YES |  |
| contratto_id | bigint | YES |  |
| magazzino_id | bigint | YES |  |
| ubicazione | character varying | YES |  |
| data_stato | timestamp with time zone | NO | now() |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | text | YES | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES | now() |
| storicizza | boolean | NO | false |
| stato_id | bigint | NO |  |
| ubicazione_id | bigint | YES |  |
| ownership_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_assets_articolo | articolo_id |
| FOREIGN KEY | fk_mag_assets_billing_account | billing_account_id |
| FOREIGN KEY | fk_mag_assets_contratto | contratto_id |
| FOREIGN KEY | fk_mag_assets_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_assets_ownership_id | ownership_id |
| FOREIGN KEY | fk_mag_assets_stato | stato_id |
| FOREIGN KEY | fk_mag_assets_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_mag_assets | id |
| UNIQUE | uq_mag_assets_seriale | seriale |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_assets_articolo_id | `CREATE INDEX ix_magazzino_assets_articolo_id ON magazzino.assets USING btree (articolo_id)` |
| ix_magazzino_assets_magazzino_id | `CREATE INDEX ix_magazzino_assets_magazzino_id ON magazzino.assets USING btree (magazzino_id)` |
| ix_magazzino_assets_ownership_id | `CREATE INDEX ix_magazzino_assets_ownership_id ON magazzino.assets USING btree (ownership_id)` |
| ix_magazzino_assets_stato_id | `CREATE INDEX ix_magazzino_assets_stato_id ON magazzino.assets USING btree (stato_id)` |
| ix_magazzino_assets_ubicazione_id | `CREATE INDEX ix_magazzino_assets_ubicazione_id ON magazzino.assets USING btree (ubicazione_id)` |
| pk_mag_assets | `CREATE UNIQUE INDEX pk_mag_assets ON magazzino.assets USING btree (id)` |
| uq_mag_assets_seriale | `CREATE UNIQUE INDEX uq_mag_assets_seriale ON magazzino.assets USING btree (seriale)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_assets_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_assets_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_assets_a10_assets_ownership_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'assets_ownership', 'attivo', 'ownership_id', 'id')` |
| trg_assets_a10_assets_ownership_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'assets_ownership', 'attivo', 'ownership_id', 'id')` |
| trg_assets_a10_eventi_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'eventi_assets', 'asset_id', 'id', 'attivo')` |
| trg_assets_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_assets_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_assets_a10_note_asset_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'note_asset', 'target_id', 'id', 'attivo')` |
| trg_assets_a10_stati_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_assets', 'attivo', 'stato_id', 'id')` |
| trg_assets_a10_stati_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_assets', 'attivo', 'stato_id', 'id')` |
| trg_assets_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_assets_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_assets_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_assets_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_assets_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_assets_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_assets_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('assets_id')` |
| trg_assets_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('assets_id')` |

---
{% include-markdown "signature-core.md" %}
