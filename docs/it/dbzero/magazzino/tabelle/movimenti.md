{% include-markdown "it/dbzero/magazzino/manual/movimenti.md" %}
# 📚 Tabella `movimenti`

> 📝 **Descrizione**
>
> Il registro dei movimenti di magazzino (ledger): una riga per ogni entrata o uscita di un articolo da un magazzino. Quattro regole. (1) La SORGENTE e' obbligatoria e a catalogo: sorgente_tipo_id verso config.sorgenti piu' esattamente una chiave fra sorgente_riga e sorgente_uid, e il record deve esistere (guard tipizzato) — non esiste un movimento senza operazione a monte: la correzione a mano E' una rettifica. (2) Il VERSO sta nella quantita': qta firmata, sign(qta) = causali.segno (guard trgfn_movimenti_guard_verso). (3) qta e' in UoM BASE dell'articolo: la conversione la fa l'operazione, non il registro. (4) L'IDENTITA' e' l'operazione-per-tranche (uq_mag_movimenti_identita). Un ledger non si spegne ne' si corregge: si storna con un movimento contrario (storno_di_movimento_id, causali STORNO_POS/STORNO_NEG). Giacenza = sum(qta) per articolo e magazzino (vw_giacenza). Perimetro: l'emittente del magazzino (RLS via_magazzino). Scrive la primitiva di Lotto 2. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.4.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | NO |  |
| qta | numeric(18,6) | NO |  |
| costo_unitario | numeric(18,6) | YES |  |
| data_mov | timestamp with time zone | NO | now() |
| causale_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |
| transfer_uid | uuid | YES |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_riga | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| lotto_id | bigint | YES |  |
| asset_id | bigint | YES |  |
| ubicazione_id | bigint | YES |  |
| storno_di_movimento_id | bigint | YES |  |
| sorgente_id | bigint | YES |  |
| sorgente_dettaglio | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_movimenti_asset_qta_unitaria |  |
| CHECK | chk_mag_movimenti_qta_non_zero |  |
| CHECK | chk_mag_movimenti_sorgente_chiave |  |
| CHECK | chk_movimenti_costo_unitario_finito |  |
| CHECK | chk_movimenti_qta_finito |  |
| FOREIGN KEY | fk_mag_movimenti_articolo | articolo_id |
| FOREIGN KEY | fk_mag_movimenti_asset | asset_id |
| FOREIGN KEY | fk_mag_movimenti_causale | causale_id |
| FOREIGN KEY | fk_mag_movimenti_lotto | lotto_id |
| FOREIGN KEY | fk_mag_movimenti_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_movimenti_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_mag_movimenti_storno_di | storno_di_movimento_id |
| FOREIGN KEY | fk_mag_movimenti_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_mag_movimenti | id |
| UNIQUE | uq_mag_movimenti_storno_di | storno_di_movimento_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_mov_transfer_uid | `CREATE INDEX ix_mag_mov_transfer_uid ON magazzino.movimenti USING btree (transfer_uid)` |
| ix_mag_movimenti_data | `CREATE INDEX ix_mag_movimenti_data ON magazzino.movimenti USING btree (data_mov)` |
| ix_magazzino_movimenti_articolo_id | `CREATE INDEX ix_magazzino_movimenti_articolo_id ON magazzino.movimenti USING btree (articolo_id)` |
| ix_magazzino_movimenti_causale_id | `CREATE INDEX ix_magazzino_movimenti_causale_id ON magazzino.movimenti USING btree (causale_id)` |
| ix_magazzino_movimenti_magazzino_id | `CREATE INDEX ix_magazzino_movimenti_magazzino_id ON magazzino.movimenti USING btree (magazzino_id)` |
| ix_movimenti_asset_id | `CREATE INDEX ix_movimenti_asset_id ON magazzino.movimenti USING btree (asset_id)` |
| ix_movimenti_lotto_id | `CREATE INDEX ix_movimenti_lotto_id ON magazzino.movimenti USING btree (lotto_id)` |
| ix_movimenti_ubicazione_id | `CREATE INDEX ix_movimenti_ubicazione_id ON magazzino.movimenti USING btree (ubicazione_id)` |
| pk_mag_movimenti | `CREATE UNIQUE INDEX pk_mag_movimenti ON magazzino.movimenti USING btree (id)` |
| uq_mag_movimenti_identita | `CREATE UNIQUE INDEX uq_mag_movimenti_identita ON magazzino.movimenti USING btree (sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, sorgente_dettaglio, causale_id, asset_id, lotto_id, ubicazione_id) NULLS NOT DISTINCT` |
| uq_mag_movimenti_storno_di | `CREATE UNIQUE INDEX uq_mag_movimenti_storno_di ON magazzino.movimenti USING btree (storno_di_movimento_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_movimenti_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_movimenti_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_movimenti_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_movimenti_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_movimenti_a10_causali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'causali', 'attivo', 'causale_id', 'id')` |
| trg_movimenti_a10_causali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'causali', 'attivo', 'causale_id', 'id')` |
| trg_movimenti_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` |
| trg_movimenti_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` |
| trg_movimenti_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DETTAGLIO', 'BLOCCA')` |
| trg_movimenti_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DETTAGLIO', 'BLOCCA')` |
| trg_movimenti_a10_guard_verso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_movimenti_guard_verso()` |
| trg_movimenti_a10_guard_verso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_movimenti_guard_verso()` |
| trg_movimenti_a10_lotti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_movimenti_a10_lotti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_movimenti_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_movimenti_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_movimenti_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_movimenti_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_movimenti_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_movimenti_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_movimenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_movimenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_movimenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_movimenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_movimenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('movimenti_id')` |
| trg_movimenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('movimenti_id')` |

---
{% include-markdown "signature-core.md" %}
