{% include-markdown "it/dbzero/vendite/manual/note.md" %}
# 📚 Tabella `note`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| target_tipo | character varying | NO |  |
| target_id | bigint | NO |  |
| target_riga_id | bigint | YES |  |
| anchor_tipo | character varying | NO |  |
| posizione | character varying | NO |  |
| seq | integer | NO | 10 |
| testo | text | YES |  |
| testo_md | text | YES |  |
| visibile | boolean | NO | true |
| solo_stampa | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| id_stile | bigint | NO |  |
| id_lingua | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| CHECK | chk_note_target_tipo |  |
| CHECK | chk_note_testo_non_vuoto |  |
| FOREIGN KEY | fk_vendite_note_id_lingua | id_lingua |
| FOREIGN KEY | fk_vendite_note_id_stile | id_stile |
| PRIMARY KEY | pk_note | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_render_order | `CREATE INDEX ix_note_render_order ON ONLY vendite.note USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| ix_vendite_note_by_riga | `CREATE INDEX ix_vendite_note_by_riga ON ONLY vendite.note USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |
| pk_note | `CREATE UNIQUE INDEX pk_note ON ONLY vendite.note USING btree (target_tipo, id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_a10_lingue_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'id_lingua')` |
| trg_note_a10_lingue_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'id_lingua')` |
| trg_note_a10_note_stili_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'note_stili', 'attivo', 'id_stile')` |
| trg_note_a10_note_stili_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'note_stili', 'attivo', 'id_stile')` |

---
{% include-markdown "signature-core.md" %}
