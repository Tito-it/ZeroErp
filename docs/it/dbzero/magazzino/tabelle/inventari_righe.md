{% include-markdown "it/dbzero/magazzino/manual/inventari_righe.md" %}
# 📚 Tabella `inventari_righe`

> 📝 **Descrizione**
>
> Conteggi fisici di inventario

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| inventario_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| qta_contata | numeric(18,6) | NO |  |
| qta_sistema | numeric(18,6) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| ubicazione_id | bigint | YES |  |
| lotto_id | bigint | YES |  |
| asset_id | bigint | YES |  |
| costo_unitario | numeric(18,6) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_inventari_righe_costo_unitario_finito |  |
| CHECK | chk_inventari_righe_qta_contata_finito |  |
| CHECK | chk_inventari_righe_qta_sistema_finito |  |
| CHECK | chk_mag_inventari_righe_asset_qta_unitaria |  |
| CHECK | chk_mag_inventari_righe_costo_non_neg |  |
| CHECK | chk_mag_inventario_righe_qta_contata_non_neg |  |
| FOREIGN KEY | fk_mag_inventari_righe_asset | asset_id |
| FOREIGN KEY | fk_mag_inventari_righe_lotto | lotto_id |
| FOREIGN KEY | fk_mag_inventari_righe_ubicazione | ubicazione_id |
| FOREIGN KEY | fk_mag_inventario_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_inventario_righe_testata | inventario_id |
| PRIMARY KEY | pk_mag_invetario_righe | id |
| UNIQUE | uq_mag_inventari_righe_posizione | inventario_id, articolo_id, ubicazione_id, lotto_id, asset_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_inventari_righe_asset_id | `CREATE INDEX ix_inventari_righe_asset_id ON magazzino.inventari_righe USING btree (asset_id)` |
| ix_inventari_righe_lotto_id | `CREATE INDEX ix_inventari_righe_lotto_id ON magazzino.inventari_righe USING btree (lotto_id)` |
| ix_magazzino_inventari_righe_articolo_id | `CREATE INDEX ix_magazzino_inventari_righe_articolo_id ON magazzino.inventari_righe USING btree (articolo_id)` |
| ix_magazzino_inventari_righe_ubicazione_id | `CREATE INDEX ix_magazzino_inventari_righe_ubicazione_id ON magazzino.inventari_righe USING btree (ubicazione_id)` |
| pk_mag_invetario_righe | `CREATE UNIQUE INDEX pk_mag_invetario_righe ON magazzino.inventari_righe USING btree (id)` |
| uq_mag_inventari_righe_posizione | `CREATE UNIQUE INDEX uq_mag_inventari_righe_posizione ON magazzino.inventari_righe USING btree (inventario_id, articolo_id, ubicazione_id, lotto_id, asset_id) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_inventari_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_inventari_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_inventari_righe_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_inventari_righe_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_inventari_righe_a10_guard_testata_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('inventari', 'inventario_id', 'stato_mag_inventario', 'zeroerp.magazzino_posting_inventario')` |
| trg_inventari_righe_a10_guard_testata_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('inventari', 'inventario_id', 'stato_mag_inventario', 'zeroerp.magazzino_posting_inventario')` |
| trg_inventari_righe_a10_guard_testata_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('inventari', 'inventario_id', 'stato_mag_inventario', 'zeroerp.magazzino_posting_inventario')` |
| trg_inventari_righe_a10_lotti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_inventari_righe_a10_lotti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_inventari_righe_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_inventari_righe_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_inventari_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_inventari_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_inventari_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_inventari_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_inventari_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('inventari_righe_id')` |
| trg_inventari_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('inventari_righe_id')` |
| trg_magazzino_inventari_righe_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
