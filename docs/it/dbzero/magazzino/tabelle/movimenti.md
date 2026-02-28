# 📚 Tabella `movimenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | NO |  |
| magazzino_id_dest | bigint | YES |  |
| uom_id | bigint | YES |  |
| qta | numeric | NO |  |
| costo_unitario | numeric | YES |  |
| data_mov | timestamp with time zone | NO | now() |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| causale_id | bigint | NO |  |
| doc_schema | character varying | NO |  |
| doc_table | character varying | NO |  |
| doc_id | bigint | NO |  |
| doc_riga_id | bigint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |
| transfer_uid | uuid | YES |  |
| ubicazione_id_from | bigint | YES |  |
| ubicazione_id_to | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_movimenti_da_destinazione_distinti |  |
| CHECK | chk_mag_movimenti_qta_non_zero |  |
| CHECK | chk_mag_movimenti_ubi_from_to_diff |  |
| FOREIGN KEY | fk_mag_movimenti_articolo | articolo_id |
| FOREIGN KEY | fk_mag_movimenti_causale | causale_id |
| FOREIGN KEY | fk_mag_movimenti_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_movimenti_magazzino_dest | magazzino_id_dest |
| FOREIGN KEY | fk_mag_movimenti_ubicazione_from | ubicazione_id_from |
| FOREIGN KEY | fk_mag_movimenti_ubicazione_to | ubicazione_id_to |
| FOREIGN KEY | fk_mag_movimenti_uom | uom_id |
| PRIMARY KEY | pk_mag_movimenti | id |
| UNIQUE | uq_mag_movimenti_docref | doc_schema, doc_table, doc_id, doc_riga_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_mov_transfer_uid | `CREATE INDEX ix_mag_mov_transfer_uid ON magazzino.movimenti USING btree (transfer_uid)` |
| ix_mag_movimenti_data | `CREATE INDEX ix_mag_movimenti_data ON magazzino.movimenti USING btree (data_mov)` |
| ix_magazzino_movimenti_articolo_id | `CREATE INDEX ix_magazzino_movimenti_articolo_id ON magazzino.movimenti USING btree (articolo_id)` |
| ix_magazzino_movimenti_causale_id | `CREATE INDEX ix_magazzino_movimenti_causale_id ON magazzino.movimenti USING btree (causale_id)` |
| ix_magazzino_movimenti_magazzino_id | `CREATE INDEX ix_magazzino_movimenti_magazzino_id ON magazzino.movimenti USING btree (magazzino_id)` |
| ix_magazzino_movimenti_magazzino_id_dest | `CREATE INDEX ix_magazzino_movimenti_magazzino_id_dest ON magazzino.movimenti USING btree (magazzino_id_dest)` |
| ix_magazzino_movimenti_ubicazione_id_from | `CREATE INDEX ix_magazzino_movimenti_ubicazione_id_from ON magazzino.movimenti USING btree (ubicazione_id_from)` |
| ix_magazzino_movimenti_ubicazione_id_to | `CREATE INDEX ix_magazzino_movimenti_ubicazione_id_to ON magazzino.movimenti USING btree (ubicazione_id_to)` |
| pk_mag_movimenti | `CREATE UNIQUE INDEX pk_mag_movimenti ON magazzino.movimenti USING btree (id)` |
| uq_mag_movimenti_docref | `CREATE UNIQUE INDEX uq_mag_movimenti_docref ON magazzino.movimenti USING btree (doc_schema, doc_table, doc_id, doc_riga_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_movimenti_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_movimenti_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id')` |
| trg_movimenti_a10_causali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'causali', 'attivo', 'causale_id')` |
| trg_movimenti_a10_causali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'causali', 'attivo', 'causale_id')` |
| trg_movimenti_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id')` |
| trg_movimenti_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id')` |
| trg_movimenti_a10_note_movimento_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'note_movimento', 'target_id', 'id')` |
| trg_movimenti_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_movimenti_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id')` |
| trg_movimenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_movimenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_movimenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_movimenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_movimenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('movimenti_id')` |
| trg_movimenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('movimenti_id')` |

---
{% include-markdown "signature-core.md" %}
