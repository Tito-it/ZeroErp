{% include-markdown "it/dbzero/catalogo/manual/note.md" %}
# 📚 Tabella `note`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| target_tipo | character varying(50) | NO |  |
| target_id | uuid | NO |  |
| target_riga_id | uuid | YES |  |
| anchor_tipo | character varying(12) | NO |  |
| posizione | character varying(12) | NO |  |
| seq | integer | NO | 10 |
| testo | text | YES |  |
| testo_md | text | YES |  |
| id_stile | bigint | NO |  |
| id_lingua | bigint | YES |  |
| visibile | boolean | NO | true |
| solo_stampa | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_catalogo_ancora_documento |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| CHECK | chk_note_testo_non_vuoto |  |
| FOREIGN KEY | fk_cat_note_id_lingua | id_lingua |
| FOREIGN KEY | fk_cat_note_id_stile | id_stile |
| FOREIGN KEY | fk_cat_note_target_tipo | target_tipo |
| PRIMARY KEY | pk_note | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_render_order | `CREATE INDEX ix_note_render_order ON ONLY catalogo.note USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| pk_note | `CREATE UNIQUE INDEX pk_note ON ONLY catalogo.note USING btree (target_tipo, id)` |

---
{% include-markdown "signature-core.md" %}
