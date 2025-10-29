{% include-markdown "it/dbzero/vendite/manual/note_fatture.md" %}
# 📚 Tabella `note_fatture`

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
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| id_stile | bigint | NO |  |
| id_lingua | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatnote_testo_non_vuoto |  |
| CHECK | chk_fatture_note_anchor |  |
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| CHECK | chk_note_target_tipo |  |
| CHECK | chk_note_testo_non_vuoto |  |
| FOREIGN KEY | fk_fatture_note_riga | target_riga_id |
| FOREIGN KEY | fk_fatture_note_testata | target_id |
| FOREIGN KEY | fk_vendite_note_id_lingua | id_lingua, id_lingua, id_lingua, id_lingua, id_lingua, id_lingua, id_lingua |
| FOREIGN KEY | fk_vendite_note_id_stile | id_stile, id_stile, id_stile, id_stile, id_stile, id_stile, id_stile |
| PRIMARY KEY | note_fatture_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_note_render | `CREATE INDEX ix_fatture_note_render ON vendite.note_fatture USING btree (target_id, anchor_tipo, target_riga_id, posizione, seq)` |
| note_fatture_pkey | `CREATE UNIQUE INDEX note_fatture_pkey ON vendite.note_fatture USING btree (target_tipo, id)` |
| note_fatture_target_tipo_target_id_anchor_tipo_posizione_se_idx | `CREATE INDEX note_fatture_target_tipo_target_id_anchor_tipo_posizione_se_idx ON vendite.note_fatture USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| note_fatture_target_tipo_target_id_target_riga_id_anchor_ti_idx | `CREATE INDEX note_fatture_target_tipo_target_id_target_riga_id_anchor_ti_idx ON vendite.note_fatture USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_fatture_ins_upd_validate | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_note_validate_generic('vendite.fatture_righe', 'fattura_id', 'FATTURA')` |
| trg_note_fatture_ins_upd_validate | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_note_validate_generic('vendite.fatture_righe', 'fattura_id', 'FATTURA')` |

---
{% include-markdown "signature-core.md" %}
