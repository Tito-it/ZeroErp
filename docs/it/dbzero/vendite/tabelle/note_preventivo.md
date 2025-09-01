# 📚 Tabella `note_preventivo`

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
| CHECK | chk_prevnote_anchor |  |
| FOREIGN KEY | fk_prevnote_riga | target_riga_id |
| FOREIGN KEY | fk_prevnote_testata | target_id |
| PRIMARY KEY | note_preventivo_pkey | id, target_tipo |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_prevnote_render | `CREATE INDEX ix_prevnote_render ON vendite.note_preventivo USING btree (target_id, anchor_tipo, target_riga_id, posizione, seq)` |
| note_preventivo_pkey | `CREATE UNIQUE INDEX note_preventivo_pkey ON vendite.note_preventivo USING btree (target_tipo, id)` |
| note_preventivo_target_tipo_target_id_anchor_tipo_posizione_idx | `CREATE INDEX note_preventivo_target_tipo_target_id_anchor_tipo_posizione_idx ON vendite.note_preventivo USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_prevnote_validate | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_prevnote_validate()` |
| trg_prevnote_validate | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_prevnote_validate()` |

---
{% include-markdown "signature-core.md" %}
