# 📚 Tabella `note_articoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| target_tipo | character varying | NO |  |
| target_id | uuid | NO |  |
| target_riga_id | uuid | YES |  |
| anchor_tipo | character varying | NO |  |
| posizione | character varying | NO |  |
| seq | integer | NO | 10 |
| testo | text | YES |  |
| testo_md | text | YES |  |
| id_stile | bigint | NO |  |
| id_lingua | bigint | YES |  |
| visibile | boolean | NO | true |
| solo_stampa | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| CHECK | chk_note_target_tipo |  |
| FOREIGN KEY | fk_cat_note_articoli_target | target_id |
| FOREIGN KEY | fk_cat_note_id_lingua | id_lingua, id_lingua, id_lingua |
| FOREIGN KEY | fk_cat_note_id_stile | id_stile, id_stile, id_stile |
| PRIMARY KEY | note_articoli_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| note_articoli_pkey | `CREATE UNIQUE INDEX note_articoli_pkey ON catalogo.note_articoli USING btree (target_tipo, id)` |
| note_articoli_target_tipo_target_id_anchor_tipo_posizione_s_idx | `CREATE INDEX note_articoli_target_tipo_target_id_anchor_tipo_posizione_s_idx ON catalogo.note_articoli USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_a10_lingue_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'id_lingua')` |
| trg_note_a10_lingue_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'id_lingua')` |
| trg_note_a10_note_stili_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'note_stili', 'attivo', 'id_stile')` |
| trg_note_a10_note_stili_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'note_stili', 'attivo', 'id_stile')` |
| trg_note_articoli_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'target_id')` |
| trg_note_articoli_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'target_id')` |
| trg_note_articoli_a10_lingue_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'id_lingua')` |
| trg_note_articoli_a10_lingue_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'id_lingua')` |
| trg_note_articoli_a10_note_stili_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'note_stili', 'attivo', 'id_stile')` |
| trg_note_articoli_a10_note_stili_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'note_stili', 'attivo', 'id_stile')` |
| trg_note_articoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
