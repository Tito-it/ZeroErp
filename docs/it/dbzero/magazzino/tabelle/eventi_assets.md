{% include-markdown "it/dbzero/magazzino/manual/eventi_assets.md" %}
# 📚 Tabella `eventi_assets`

> 📝 **Descrizione**
>
> Eventi di vita asset: installazione, rientro, swap, manutenzione, ecc.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| asset_id | bigint | NO |  |
| data_evento | timestamp with time zone | NO | now() |
| magazzino_id_from | bigint | YES |  |
| magazzino_id_to | bigint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | text | YES |  |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |
| storicizza | boolean | NO | false |
| tipo_evento_id | bigint | NO |  |
| stato_da_id | bigint | YES |  |
| stato_a_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| sorgente_riga | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_eventi_assets_da_a_distinti |  |
| CHECK | chk_mag_eventi_assets_sorgente_chiave |  |
| FOREIGN KEY | fk_mag_eventi_assets_asset | asset_id |
| FOREIGN KEY | fk_mag_eventi_assets_magazzino_from | magazzino_id_from |
| FOREIGN KEY | fk_mag_eventi_assets_magazzino_to | magazzino_id_to |
| FOREIGN KEY | fk_mag_eventi_assets_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_mag_eventi_assets_tipo_evento | tipo_evento_id |
| PRIMARY KEY | pk_mag_eventi_assets | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_eventi_assets_data | `CREATE INDEX ix_mag_eventi_assets_data ON magazzino.eventi_assets USING btree (data_evento)` |
| ix_mag_eventi_assets_stato_a_id | `CREATE INDEX ix_mag_eventi_assets_stato_a_id ON magazzino.eventi_assets USING btree (stato_a_id)` |
| ix_mag_eventi_assets_stato_da_id | `CREATE INDEX ix_mag_eventi_assets_stato_da_id ON magazzino.eventi_assets USING btree (stato_da_id)` |
| ix_magazzino_eventi_assets_asset_id | `CREATE INDEX ix_magazzino_eventi_assets_asset_id ON magazzino.eventi_assets USING btree (asset_id)` |
| ix_magazzino_eventi_assets_tipo_evento_id | `CREATE INDEX ix_magazzino_eventi_assets_tipo_evento_id ON magazzino.eventi_assets USING btree (tipo_evento_id)` |
| pk_mag_eventi_assets | `CREATE UNIQUE INDEX pk_mag_eventi_assets ON magazzino.eventi_assets USING btree (id)` |
| uq_mag_eventi_assets_sorgente_fk | `CREATE UNIQUE INDEX uq_mag_eventi_assets_sorgente_fk ON magazzino.eventi_assets USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_eventi_assets_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_eventi_assets_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_eventi_assets_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_tipizzata()` |
| trg_eventi_assets_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa_tipizzata()` |
| trg_eventi_assets_a10_note_evento_asset_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'note_evento_asset', 'target_id', 'id', 'attivo')` |
| trg_eventi_assets_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_eventi_assets_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_eventi_assets_a10_tipi_evento_assets_require_attivo__5f1efd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_evento_assets', 'attivo', 'tipo_evento_id', 'id')` |
| trg_eventi_assets_a10_tipi_evento_assets_require_attivo__5f1efd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_evento_assets', 'attivo', 'tipo_evento_id', 'id')` |
| trg_eventi_assets_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_eventi_assets_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_eventi_assets_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_eventi_assets_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_eventi_assets_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('eventi_assets_id')` |
| trg_eventi_assets_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('eventi_assets_id')` |
| trg_magazzino_eventi_assets_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
