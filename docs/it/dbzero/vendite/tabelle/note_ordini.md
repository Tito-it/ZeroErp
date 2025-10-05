# 📚 Tabella `note_ordini`

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
| stile | character varying | NO | 'NORMALE'::character varying |
| lingua | character | YES |  |
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
| CHECK | chk_ordini_note_anchor |  |
| FOREIGN KEY | fk_ordini_note_riga | target_riga_id |
| FOREIGN KEY | fk_ordini_note_testata | target_id |
| PRIMARY KEY | note_ordini_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_note_render | `CREATE INDEX ix_ordini_note_render ON vendite.note_ordini USING btree (target_id, anchor_tipo, target_riga_id, posizione, seq)` |
| note_ordini_pkey | `CREATE UNIQUE INDEX note_ordini_pkey ON vendite.note_ordini USING btree (target_tipo, id)` |
| note_ordini_target_tipo_target_id_anchor_tipo_posizione_seq_idx | `CREATE INDEX note_ordini_target_tipo_target_id_anchor_tipo_posizione_seq_idx ON vendite.note_ordini USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| note_ordini_target_tipo_target_id_target_riga_id_anchor_tip_idx | `CREATE INDEX note_ordini_target_tipo_target_id_target_riga_id_anchor_tip_idx ON vendite.note_ordini USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |

---
{% include-markdown "signature-core.md" %}
