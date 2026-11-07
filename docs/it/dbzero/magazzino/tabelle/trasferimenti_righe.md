{% include-markdown "it/dbzero/magazzino/manual/trasferimenti_righe.md" %}
# 📚 Tabella `trasferimenti_righe`

> 📝 **Descrizione**
>
> Righe del trasferimento

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| trasferimento_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| qta | numeric(18,6) | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| lotto_id | bigint | YES |  |
| asset_id | bigint | YES |  |
| ubicazione_id_da | bigint | YES |  |
| ubicazione_id_a | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_trasferimenti_qta_pos |  |
| CHECK | chk_mag_trasferimenti_righe_asset_qta_unitaria |  |
| CHECK | chk_mag_trasferimenti_righe_ubicazioni_distinte |  |
| CHECK | chk_trasferimenti_righe_qta_finito |  |
| FOREIGN KEY | fk_mag_trasferimenti_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_trasferimenti_righe_asset | asset_id |
| FOREIGN KEY | fk_mag_trasferimenti_righe_lotto | lotto_id |
| FOREIGN KEY | fk_mag_trasferimenti_righe_testata | trasferimento_id |
| FOREIGN KEY | fk_mag_trasferimenti_righe_ubicazione_a | ubicazione_id_a |
| FOREIGN KEY | fk_mag_trasferimenti_righe_ubicazione_da | ubicazione_id_da |
| PRIMARY KEY | pk_mag_trasferimenti_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_trasferimenti_righe_articolo_id | `CREATE INDEX ix_magazzino_trasferimenti_righe_articolo_id ON magazzino.trasferimenti_righe USING btree (articolo_id)` |
| ix_trasferimenti_righe_asset_id | `CREATE INDEX ix_trasferimenti_righe_asset_id ON magazzino.trasferimenti_righe USING btree (asset_id)` |
| ix_trasferimenti_righe_lotto_id | `CREATE INDEX ix_trasferimenti_righe_lotto_id ON magazzino.trasferimenti_righe USING btree (lotto_id)` |
| pk_mag_trasferimenti_righe | `CREATE UNIQUE INDEX pk_mag_trasferimenti_righe ON magazzino.trasferimenti_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_magazzino_trasferimenti_righe_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_trasferimenti_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_trasferimenti_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_trasferimenti_righe_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_trasferimenti_righe_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_trasferimenti_righe_a10_guard_testata_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('trasferimenti', 'trasferimento_id', 'stato_trasferimento', 'zeroerp.magazzino_posting_trasferimento')` |
| trg_trasferimenti_righe_a10_guard_testata_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('trasferimenti', 'trasferimento_id', 'stato_trasferimento', 'zeroerp.magazzino_posting_trasferimento')` |
| trg_trasferimenti_righe_a10_guard_testata_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_documento_interno_righe_guard_testata('trasferimenti', 'trasferimento_id', 'stato_trasferimento', 'zeroerp.magazzino_posting_trasferimento')` |
| trg_trasferimenti_righe_a10_lotti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_trasferimenti_righe_a10_lotti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_trasferimenti_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_trasferimenti_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_trasferimenti_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_trasferimenti_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_trasferimenti_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('trasferimenti_righe_id')` |
| trg_trasferimenti_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('trasferimenti_righe_id')` |

---
{% include-markdown "signature-core.md" %}
