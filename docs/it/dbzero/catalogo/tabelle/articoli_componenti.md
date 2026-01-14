{% include-markdown "it/dbzero/catalogo/manual/articoli_componenti.md" %}
# 📚 Tabella `articoli_componenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| prodotto_id | uuid | NO |  |
| componente_id | uuid | NO |  |
| coeff_qta | numeric | NO | 1 |
| partecipa_qta | boolean | NO | false |
| obbligatorio | boolean | NO | true |
| valid_from | date | NO |  |
| valid_to | date | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| attivo | boolean | NO | true |
| note_target_tipo | character varying | YES |  |
| note_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_articoli_componenti_coeff_qta_pos |  |
| CHECK | chk_articoli_componenti_no_selfref |  |
| CHECK | chk_articoli_componenti_note_target_tipo |  |
| CHECK | chk_articoli_componenti_valid_dates |  |
| FOREIGN KEY | fk_articoli_componenti_articoli_componente | componente_id |
| FOREIGN KEY | fk_articoli_componenti_articoli_prodotto | prodotto_id |
| FOREIGN KEY | fk_articoli_componenti_note | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_componenti_note_1 | note_target_tipo, note_id |
| FOREIGN KEY | fk_articoli_componenti_note_2 | note_target_tipo, note_id |
| PRIMARY KEY | pk_articoli_componenti | id |
| UNIQUE | uq_articoli_componenti_prodotto_componente_from | valid_from, prodotto_id, componente_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_articoli_componenti_no_overlap | `CREATE INDEX ex_articoli_componenti_no_overlap ON catalogo.articoli_componenti USING gist (prodotto_id, componente_id, daterange(valid_from, COALESCE(valid_to, 'infinity'::date), '[]'::text))` |
| ix_articoli_componenti_componente_from_to | `CREATE INDEX ix_articoli_componenti_componente_from_to ON catalogo.articoli_componenti USING btree (componente_id, valid_from, valid_to)` |
| ix_articoli_componenti_no_overlap_gist | `CREATE INDEX ix_articoli_componenti_no_overlap_gist ON catalogo.articoli_componenti USING gist (prodotto_id, componente_id, daterange(valid_from, COALESCE(valid_to, 'infinity'::date), '[]'::text))` |
| ix_articoli_componenti_prodotto_from_to | `CREATE INDEX ix_articoli_componenti_prodotto_from_to ON catalogo.articoli_componenti USING btree (prodotto_id, valid_from, valid_to)` |
| pk_articoli_componenti | `CREATE UNIQUE INDEX pk_articoli_componenti ON catalogo.articoli_componenti USING btree (id)` |
| uq_articoli_componenti_prodotto_componente_from | `CREATE UNIQUE INDEX uq_articoli_componenti_prodotto_componente_from ON catalogo.articoli_componenti USING btree (prodotto_id, componente_id, valid_from)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_componenti_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id')` |
| trg_articoli_componenti_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'componente_id')` |
| trg_articoli_componenti_a10_note_articoli_componenti_blo_a2749a | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'note_articoli_componenti', 'target_id', 'id')` |
| trg_articoli_componenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_componenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_componenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_componenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_componenti_id')` |
| trg_articoli_componenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_componenti_id')` |

---
{% include-markdown "signature-core.md" %}
