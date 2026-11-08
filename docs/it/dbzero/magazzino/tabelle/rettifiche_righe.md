{% include-markdown "it/dbzero/magazzino/manual/rettifiche_righe.md" %}
# 📚 Tabella `rettifiche_righe`

> 📝 **Descrizione**
>
> Righe di rettifica (delta quantità)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| rettifica_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| qta_delta | numeric(18,6) | NO |  |
| motivo | character varying(64) | YES |  |
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
| CHECK | chk_mag_rettifiche_qta_non_zero |  |
| CHECK | chk_mag_rettifiche_righe_asset_qta_unitaria |  |
| CHECK | chk_mag_rettifiche_righe_costo_non_neg |  |
| CHECK | chk_rettifiche_righe_costo_unitario_finito |  |
| CHECK | chk_rettifiche_righe_qta_delta_finito |  |
| FOREIGN KEY | fk_mag_rettifiche_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_rettifiche_righe_asset | asset_id |
| FOREIGN KEY | fk_mag_rettifiche_righe_lotto | lotto_id |
| FOREIGN KEY | fk_mag_rettifiche_righe_testata | rettifica_id |
| FOREIGN KEY | fk_mag_rettifiche_righe_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_mag_rettifiche_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_rettifiche_righe_articolo_id | `CREATE INDEX ix_magazzino_rettifiche_righe_articolo_id ON magazzino.rettifiche_righe USING btree (articolo_id)` |
| ix_magazzino_rettifiche_righe_ubicazione_id | `CREATE INDEX ix_magazzino_rettifiche_righe_ubicazione_id ON magazzino.rettifiche_righe USING btree (ubicazione_id)` |
| ix_rettifiche_righe_asset_id | `CREATE INDEX ix_rettifiche_righe_asset_id ON magazzino.rettifiche_righe USING btree (asset_id)` |
| ix_rettifiche_righe_lotto_id | `CREATE INDEX ix_rettifiche_righe_lotto_id ON magazzino.rettifiche_righe USING btree (lotto_id)` |
| pk_mag_rettifiche_righe | `CREATE UNIQUE INDEX pk_mag_rettifiche_righe ON magazzino.rettifiche_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_magazzino_rettifiche_righe_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_rettifiche_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_rettifiche_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_rettifiche_righe_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_rettifiche_righe_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_rettifiche_righe_a10_guard_testata_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('rettifiche', 'rettifica_id', 'stato_mag_rettifiche', 'zeroerp.magazzino_posting_rettifica')` |
| trg_rettifiche_righe_a10_guard_testata_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('rettifiche', 'rettifica_id', 'stato_mag_rettifiche', 'zeroerp.magazzino_posting_rettifica')` |
| trg_rettifiche_righe_a10_guard_testata_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('rettifiche', 'rettifica_id', 'stato_mag_rettifiche', 'zeroerp.magazzino_posting_rettifica')` |
| trg_rettifiche_righe_a10_lotti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_rettifiche_righe_a10_lotti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_rettifiche_righe_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_rettifiche_righe_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_rettifiche_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_rettifiche_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_rettifiche_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_rettifiche_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_rettifiche_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('rettifiche_righe_id')` |
| trg_rettifiche_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('rettifiche_righe_id')` |

---
{% include-markdown "signature-core.md" %}
