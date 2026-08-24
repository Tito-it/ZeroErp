{% include-markdown "it/dbzero/magazzino/manual/reservations.md" %}
# 📚 Tabella `reservations`

> 📝 **Descrizione**
>
> Prenotazioni stock per ordini e ODL

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | YES |  |
| qta | numeric | NO |  |
| stato_reservation | character varying | NO | 'planned'::character varying |
| data_prevista | timestamp with time zone | YES |  |
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
| ubicazione_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_res_qta_pos |  |
| CHECK | chk_mag_res_stato |  |
| FOREIGN KEY | fk_mag_reservations_articolo | articolo_id |
| FOREIGN KEY | fk_mag_reservations_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_reservations_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_mag_reservations | id |
| UNIQUE | uq_mag_reservations_docref | doc_schema, doc_table, doc_id, doc_riga_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_res_stato | `CREATE INDEX ix_mag_res_stato ON magazzino.reservations USING btree (stato_reservation)` |
| ix_magazzino_reservations_articolo_id | `CREATE INDEX ix_magazzino_reservations_articolo_id ON magazzino.reservations USING btree (articolo_id)` |
| ix_magazzino_reservations_magazzino_id | `CREATE INDEX ix_magazzino_reservations_magazzino_id ON magazzino.reservations USING btree (magazzino_id)` |
| ix_magazzino_reservations_ubicazione_id | `CREATE INDEX ix_magazzino_reservations_ubicazione_id ON magazzino.reservations USING btree (ubicazione_id)` |
| pk_mag_reservations | `CREATE UNIQUE INDEX pk_mag_reservations ON magazzino.reservations USING btree (id)` |
| uq_mag_reservations_docref | `CREATE UNIQUE INDEX uq_mag_reservations_docref ON magazzino.reservations USING btree (doc_schema, doc_table, doc_id, doc_riga_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_reservations_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_reservations_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_reservations_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_reservations_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_reservations_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_reservations_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_reservations_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_reservations_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_reservations_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_reservations_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_reservations_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('reservations_id')` |
| trg_reservations_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('reservations_id')` |

---
{% include-markdown "signature-core.md" %}
