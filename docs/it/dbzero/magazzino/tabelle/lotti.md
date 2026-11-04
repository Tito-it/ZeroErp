{% include-markdown "it/dbzero/magazzino/manual/lotti.md" %}
# 📚 Tabella `lotti`

> 📝 **Descrizione**
>
> Partita di merce di un articolo: i pezzi arrivati (o prodotti) insieme, con la data da cui si conta la rotazione e l'eventuale scadenza. E' l'unita' della tracciabilita' (FIFO fisico, richiamo di un lotto) e la dimensione che movimenti.lotto_id e le righe di inventario/rettifica/trasferimento nominano, quando catalogo.articoli.requires_lotto lo pretende. Chiave naturale (articolo_id, codice): lo stesso codice su due articoli e' legittimo, una numerazione globale non la possiede nessuno. Fuori dal perimetro RLS (definizione senza magazzino ne' emittente). Storicizzazione permanente: «chi ha cambiato la scadenza di questo lotto» e' una domanda della tracciabilita'. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.3 (M-5).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| codice | character varying(64) | NO |  |
| data_arrivo | date | NO |  |
| data_scadenza | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_lotti_codice_non_vuoto |  |
| CHECK | chk_mag_lotti_scadenza_dopo_arrivo |  |
| FOREIGN KEY | fk_mag_lotti_articolo | articolo_id |
| PRIMARY KEY | pk_mag_lotti | id |
| UNIQUE | uq_mag_lotti_articolo_codice | articolo_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_mag_lotti | `CREATE UNIQUE INDEX pk_mag_lotti ON magazzino.lotti USING btree (id)` |
| uq_mag_lotti_articolo_codice | `CREATE UNIQUE INDEX uq_mag_lotti_articolo_codice ON magazzino.lotti USING btree (articolo_id, codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_lotti_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_lotti_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_lotti_a10_ddt_righe_prelievi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_prelievi', 'lotto_id', 'id', 'attivo')` |
| trg_lotti_a10_inventari_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'inventari_righe', 'lotto_id', 'id', 'attivo')` |
| trg_lotti_a10_movimenti_attesi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti_attesi', 'lotto_id', 'id', 'attivo')` |
| trg_lotti_a10_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'movimenti', 'lotto_id', 'id', 'attivo')` |
| trg_lotti_a10_rettifiche_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'rettifiche_righe', 'lotto_id', 'id', 'attivo')` |
| trg_lotti_a10_trasferimenti_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'trasferimenti_righe', 'lotto_id', 'id', 'attivo')` |
| trg_lotti_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_lotti_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_lotti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_lotti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_lotti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_lotti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_lotti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('lotti_id')` |
| trg_lotti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('lotti_id')` |

---
{% include-markdown "signature-core.md" %}
