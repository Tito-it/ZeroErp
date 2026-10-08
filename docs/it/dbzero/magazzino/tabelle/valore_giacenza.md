{% include-markdown "it/dbzero/magazzino/manual/valore_giacenza.md" %}
# 📚 Tabella `valore_giacenza`

> 📝 **Descrizione**
>
> Il VALORE della giacenza di un articolo in un magazzino: copia ricostruibile dal registro, tenuta aggiornata dalla primitiva di scrittura (Lotto 2). Il ricalcolo e' una RI-SOMMA dei costo_unitario scritti su magazzino.movimenti (entrate al costo di documento, uscite alla media corrente), non una ri-esecuzione. La QUANTITA' non sta qui: vive solo nel registro (vw_giacenza); costo medio = valore / qta, in vw_costo_medio. Si chiamava costo_medio e portava qta fino al 2026-09-15 (M-4). Una riga per (articolo, magazzino). Nessuna nota: una copia non ha un autore (D-L1-e). Perimetro: l'emittente del magazzino. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.6.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | NO |  |
| valore | numeric(18,6) | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_valore_giacenza_articolo | articolo_id |
| FOREIGN KEY | fk_mag_valore_giacenza_magazzino | magazzino_id |
| PRIMARY KEY | pk_mag_valore_giacenza | id |
| UNIQUE | uq_mag_valore_giacenza_art_mag | articolo_id, magazzino_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_valore_giacenza_magazzino_id | `CREATE INDEX ix_magazzino_valore_giacenza_magazzino_id ON magazzino.valore_giacenza USING btree (magazzino_id)` |
| pk_mag_valore_giacenza | `CREATE UNIQUE INDEX pk_mag_valore_giacenza ON magazzino.valore_giacenza USING btree (id)` |
| uq_mag_valore_giacenza_art_mag | `CREATE UNIQUE INDEX uq_mag_valore_giacenza_art_mag ON magazzino.valore_giacenza USING btree (articolo_id, magazzino_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_valore_giacenza_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_valore_giacenza_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_valore_giacenza_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` |
| trg_valore_giacenza_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('magazzino', 'magazzino_id')` |
| trg_valore_giacenza_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_valore_giacenza_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_valore_giacenza_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_valore_giacenza_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
