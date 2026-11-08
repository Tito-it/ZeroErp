{% include-markdown "it/dbzero/magazzino/manual/movimenti_attesi.md" %}
# 📚 Tabella `movimenti_attesi`

> 📝 **Descrizione**
>
> I movimenti che DEVONO ancora accadere e che nessun documento sa: il blocco manuale di merce per qualcuno e la merce prelevata non ancora uscita. Cio' che un documento dice (impegnato da ordine, in arrivo da ordine fornitore) NON sta qui: si legge dalle righe del documento. Stessa forma del ledger: qta firmata (sign = causali.segno), sorgente a catalogo — facoltativa, perche' il blocco manuale non ha documento — e allora per chi e' lo dice il soggetto o la nota. Lo stato risponde a una domanda sola, «conta ancora?»: APERTA o CHIUSA con data_chiusura; non ha attivo. Si chiamava reservations fino al 2026-09-15 (analisi carico e scarico, sezione 7-bis: «picked e' di sola uscita»). Perimetro: l'emittente del magazzino (magazzino_id NOT NULL, RLS via_magazzino). Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.5.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | NO |  |
| qta | numeric(18,6) | NO |  |
| data_prevista | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |
| ubicazione_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_riga | bigint | YES |  |
| sorgente_uid | uuid | YES |  |
| causale_id | bigint | NO |  |
| stato | character varying(12) | NO | 'APERTA'::character varying |
| data_chiusura | timestamp with time zone | YES |  |
| soggetto_ruolo_id | bigint | YES |  |
| nota | text | YES |  |
| lotto_id | bigint | YES |  |
| asset_id | bigint | YES |  |
| sorgente_id | bigint | YES |  |
| sorgente_dettaglio | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_movimenti_attesi_asset_qta_unitaria |  |
| CHECK | chk_mag_movimenti_attesi_chiusura |  |
| CHECK | chk_mag_movimenti_attesi_data_solo_senza_documento |  |
| CHECK | chk_mag_movimenti_attesi_per_chi |  |
| CHECK | chk_mag_movimenti_attesi_qta_non_zero |  |
| CHECK | chk_mag_movimenti_attesi_sorgente_chiave |  |
| CHECK | chk_mag_movimenti_attesi_stato |  |
| CHECK | chk_movimenti_attesi_qta_finito |  |
| FOREIGN KEY | fk_mag_movimenti_attesi_articolo | articolo_id |
| FOREIGN KEY | fk_mag_movimenti_attesi_asset | asset_id |
| FOREIGN KEY | fk_mag_movimenti_attesi_causale | causale_id |
| FOREIGN KEY | fk_mag_movimenti_attesi_lotto | lotto_id |
| FOREIGN KEY | fk_mag_movimenti_attesi_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_movimenti_attesi_soggetto_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_mag_movimenti_attesi_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_mag_movimenti_attesi_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_mag_movimenti_attesi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_movimenti_attesi_aperte | `CREATE INDEX ix_mag_movimenti_attesi_aperte ON magazzino.movimenti_attesi USING btree (articolo_id, magazzino_id) WHERE ((stato)::text = 'APERTA'::text)` |
| ix_magazzino_movimenti_attesi_articolo_id | `CREATE INDEX ix_magazzino_movimenti_attesi_articolo_id ON magazzino.movimenti_attesi USING btree (articolo_id)` |
| ix_magazzino_movimenti_attesi_magazzino_id | `CREATE INDEX ix_magazzino_movimenti_attesi_magazzino_id ON magazzino.movimenti_attesi USING btree (magazzino_id)` |
| ix_magazzino_movimenti_attesi_ubicazione_id | `CREATE INDEX ix_magazzino_movimenti_attesi_ubicazione_id ON magazzino.movimenti_attesi USING btree (ubicazione_id)` |
| pk_mag_movimenti_attesi | `CREATE UNIQUE INDEX pk_mag_movimenti_attesi ON magazzino.movimenti_attesi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_movimenti_attesi_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_movimenti_attesi_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_movimenti_attesi_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_movimenti_attesi_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'asset_id', 'id')` |
| trg_movimenti_attesi_a10_causali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'causali', 'attivo', 'causale_id', 'id')` |
| trg_movimenti_attesi_a10_causali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'causali', 'attivo', 'causale_id', 'id')` |
| trg_movimenti_attesi_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` |
| trg_movimenti_attesi_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` |
| trg_movimenti_attesi_a10_guard_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_movimenti_attesi_a10_guard_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA')` |
| trg_movimenti_attesi_a10_guard_verso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_movimenti_guard_verso()` |
| trg_movimenti_attesi_a10_guard_verso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_movimenti_guard_verso()` |
| trg_movimenti_attesi_a10_lotti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_movimenti_attesi_a10_lotti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'lotti', 'attivo', 'lotto_id', 'id')` |
| trg_movimenti_attesi_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_movimenti_attesi_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_movimenti_attesi_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_movimenti_attesi_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_movimenti_attesi_a10_ubicazioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_movimenti_attesi_a10_ubicazioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'ubicazioni', 'attivo', 'ubicazione_id', 'id')` |
| trg_movimenti_attesi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_movimenti_attesi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_movimenti_attesi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_movimenti_attesi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_movimenti_attesi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('movimenti_attesi_id')` |
| trg_movimenti_attesi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('movimenti_attesi_id')` |

---
{% include-markdown "signature-core.md" %}
