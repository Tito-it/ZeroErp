{% include-markdown "it/dbzero/magazzino/manual/ubicazioni.md" %}
# 📚 Tabella `ubicazioni`

> 📝 **Descrizione**
>
> Anagrafica ubicazioni/bin per magazzini (PICK/STORAGE/STAGING/IN_TRANSIT/…)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| magazzino_id | bigint | NO |  |
| codice | character varying(64) | NO |  |
| descrizione | character varying(120) | YES |  |
| tipo_id | bigint | NO |  |
| parent_id | bigint | YES |  |
| area | character varying(32) | YES |  |
| corsia | character varying(32) | YES |  |
| scaffale | character varying(32) | YES |  |
| piano | character varying(32) | YES |  |
| posizione | character varying(32) | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_tipi_ubicazione_magazzino | tipo_id |
| FOREIGN KEY | fk_mag_ubicazioni_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_ubicazioni_parent | parent_id |
| PRIMARY KEY | pk_mag_ubicazioni | id |
| UNIQUE | uq_mag_ubicazioni_mag_codice | magazzino_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_ubicazioni_parent_id | `CREATE INDEX ix_magazzino_ubicazioni_parent_id ON magazzino.ubicazioni USING btree (parent_id)` |
| ix_magazzino_ubicazioni_tipo_id | `CREATE INDEX ix_magazzino_ubicazioni_tipo_id ON magazzino.ubicazioni USING btree (tipo_id)` |
| pk_mag_ubicazioni | `CREATE UNIQUE INDEX pk_mag_ubicazioni ON magazzino.ubicazioni USING btree (id)` |
| uq_mag_ubicazioni_mag_codice | `CREATE UNIQUE INDEX uq_mag_ubicazioni_mag_codice ON magazzino.ubicazioni USING btree (magazzino_id, codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ubicazioni_a10_ddt_righe_prelievi_block_deact_upd_593fdf | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_prelievi', 'ubicazione_arrivo_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_ddt_righe_prelievi_block_deact_upd_fb1afc | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_prelievi', 'ubicazione_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_inventari_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari_righe', 'ubicazione_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('magazzino_id', 'E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE')` |
| trg_ubicazioni_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_ubicazioni_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_ubicazioni_a10_movimenti_attesi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti_attesi', 'ubicazione_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'ubicazione_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_parent_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_ubicazioni_guard_parent()` |
| trg_ubicazioni_a10_parent_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_ubicazioni_guard_parent()` |
| trg_ubicazioni_a10_resi_righe_rientri_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe_rientri', 'ubicazione_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_rettifiche_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche_righe', 'ubicazione_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_tipi_ubicazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_ubicazione', 'attivo', 'tipo_id', 'id')` |
| trg_ubicazioni_a10_tipi_ubicazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_ubicazione', 'attivo', 'tipo_id', 'id')` |
| trg_ubicazioni_a10_ubicazioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'ubicazioni', 'parent_id', 'id', 'attivo')` |
| trg_ubicazioni_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'parent_id', 'id')` |
| trg_ubicazioni_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'parent_id', 'id')` |
| trg_ubicazioni_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_ubicazioni_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_ubicazioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ubicazioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
