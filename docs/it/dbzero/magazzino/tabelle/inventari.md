{% include-markdown "it/dbzero/magazzino/manual/inventari.md" %}
# 📚 Tabella `inventari`

> 📝 **Descrizione**
>
> Documento conteggio fisico inventario

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| data | date | NO | script.fn_data_operativa() |
| stato_mag_inventario | character varying(16) | NO | 'DRAFT'::character varying |
| magazzino_id | bigint | NO |  |
| descrizione | character varying(255) | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| sorgente_riga | bigint | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_inventari_sorgente_forma |  |
| CHECK | chk_mag_inventari_stato |  |
| FOREIGN KEY | fk_mag_inventari_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_inventari_sorgenti_tipo | sorgente_tipo_id |
| PRIMARY KEY | pk_mag_inv | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_inventari_sorgente_id | `CREATE INDEX ix_mag_inventari_sorgente_id ON magazzino.inventari USING btree (sorgente_tipo_id, sorgente_id) WHERE (sorgente_id IS NOT NULL)` |
| ix_mag_inventari_sorgente_riga | `CREATE INDEX ix_mag_inventari_sorgente_riga ON magazzino.inventari USING btree (sorgente_tipo_id, sorgente_riga) WHERE (sorgente_riga IS NOT NULL)` |
| ix_mag_inventari_sorgente_uid | `CREATE INDEX ix_mag_inventari_sorgente_uid ON magazzino.inventari USING btree (sorgente_tipo_id, sorgente_uid) WHERE (sorgente_uid IS NOT NULL)` |
| ix_mag_invetario_data | `CREATE INDEX ix_mag_invetario_data ON magazzino.inventari USING btree (data)` |
| ix_mag_invetario_stato_inventario | `CREATE INDEX ix_mag_invetario_stato_inventario ON magazzino.inventari USING btree (stato_mag_inventario)` |
| pk_mag_inv | `CREATE UNIQUE INDEX pk_mag_inv ON magazzino.inventari USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_inventari_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_inventari_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_inventari_a10_guard_transizione_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_guard_transizione('stato_mag_inventario', 'zeroerp.magazzino_posting_inventario')` |
| trg_inventari_a10_guard_transizione_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_guard_transizione('stato_mag_inventario', 'zeroerp.magazzino_posting_inventario')` |
| trg_inventari_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('magazzino_id', 'E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE')` |
| trg_inventari_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_inventari_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_inventari_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_inventari_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_inventari_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_inventari_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_inventari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_inventari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_inventari_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('inventari_id')` |
| trg_inventari_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('inventari_id')` |
| trg_magazzino_inventari_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |

---
{% include-markdown "signature-core.md" %}
