{% include-markdown "it/dbzero/catalogo/manual/articoli_componenti.md" %}
# 📚 Tabella `articoli_componenti`

> 📝 **Descrizione**
>
> Distinta base (vendita) con versioning da/a

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| prodotto_id | uuid | NO |  |
| componente_id | uuid | NO |  |
| coeff_qta | numeric(18,6) | NO | 1 |
| obbligatorio | boolean | NO | true |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| attivo | boolean | NO | true |
| note_target_tipo | character varying(32) | YES |  |
| note_id | bigint | YES |  |
| esposizione_in_fattura | character varying(40) | NO | 'NASCOSTO'::character varying |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_articoli_componenti_coeff_qta_finito |  |
| CHECK | chk_articoli_componenti_coeff_qta_pos |  |
| CHECK | chk_articoli_componenti_no_selfref |  |
| CHECK | chk_articoli_componenti_note_target_tipo |  |
| FOREIGN KEY | fk_articoli_componenti_articoli_componente | componente_id |
| FOREIGN KEY | fk_articoli_componenti_articoli_prodotto | prodotto_id |
| FOREIGN KEY | fk_articoli_componenti_esposizioni_componente | esposizione_in_fattura |
| FOREIGN KEY | fk_articoli_componenti_note | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_componenti_note_1 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_componenti_note_2 | note_target_tipo, note_id |
| PRIMARY KEY | pk_articoli_componenti | id |
| UNIQUE | uq_articoli_componenti_id_temporal | id, validita |
| UNIQUE | uq_articoli_componenti_no_overlap | prodotto_id, componente_id, validita |
| UNIQUE | uq_articoli_componenti_prodotto_componente_from | prodotto_id, componente_id, valido_dal |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_componenti_componente_from_to | `CREATE INDEX ix_articoli_componenti_componente_from_to ON catalogo.articoli_componenti USING btree (componente_id, valido_dal, valido_al)` |
| ix_articoli_componenti_prodotto_from_to | `CREATE INDEX ix_articoli_componenti_prodotto_from_to ON catalogo.articoli_componenti USING btree (prodotto_id, valido_dal, valido_al)` |
| pk_articoli_componenti | `CREATE UNIQUE INDEX pk_articoli_componenti ON catalogo.articoli_componenti USING btree (id)` |
| uq_articoli_componenti_id_temporal | `CREATE UNIQUE INDEX uq_articoli_componenti_id_temporal ON catalogo.articoli_componenti USING gist (id, validita)` |
| uq_articoli_componenti_no_overlap | `CREATE UNIQUE INDEX uq_articoli_componenti_no_overlap ON catalogo.articoli_componenti USING gist (prodotto_id, componente_id, validita)` |
| uq_articoli_componenti_prodotto_componente_from | `CREATE UNIQUE INDEX uq_articoli_componenti_prodotto_componente_from ON catalogo.articoli_componenti USING btree (prodotto_id, componente_id, valido_dal)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_componenti_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id', 'id')` |
| trg_articoli_componenti_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id', 'id')` |
| trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_block_modifica_struttura()` |
| trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_block_modifica_struttura()` |
| trg_articoli_componenti_a10_block_solo_componente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_guard_solo_componente()` |
| trg_articoli_componenti_a10_block_solo_componente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_guard_solo_componente()` |
| trg_articoli_componenti_a10_contratti_righe_componenti_b_a08565 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti_righe_componenti', 'articolo_componente_id', 'id', 'attivo')` |
| trg_articoli_componenti_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_articoli_componenti_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_articoli_componenti_a10_ddt_righe_componenti_block_d_910186 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt_righe_componenti', 'articolo_componente_id', 'id', 'attivo')` |
| trg_articoli_componenti_a10_guard_is_composito_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_guard_is_composito()` |
| trg_articoli_componenti_a10_guard_is_composito_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_guard_is_composito()` |
| trg_articoli_componenti_a10_guard_riga_componente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_guard_componente()` |
| trg_articoli_componenti_a10_guard_riga_componente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_componenti_guard_componente()` |
| trg_articoli_componenti_a10_listini_righe_componenti_blo_da0ba1 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe_componenti', 'articolo_componente_id', 'id', 'attivo')` |
| trg_articoli_componenti_a10_note_articoli_componenti_blo_a2749a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'note_articoli_componenti', 'target_id', 'id', 'attivo')` |
| trg_articoli_componenti_a10_offerte_commerciali_eccezion_1e1bf7 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali_eccezioni_componenti', 'articolo_componente_id', 'id', 'attivo')` |
| trg_articoli_componenti_a10_ordini_righe_componenti_bloc_a72450 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini_righe_componenti', 'articolo_componente_id', 'id', 'attivo')` |
| trg_articoli_componenti_a10_preventivi_righe_componenti__48a14a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi_righe_componenti', 'articolo_componente_id', 'id', 'attivo')` |
| trg_articoli_componenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_componenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_componenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_componenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_componenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_componenti_id')` |
| trg_articoli_componenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_componenti_id')` |

---
{% include-markdown "signature-core.md" %}
