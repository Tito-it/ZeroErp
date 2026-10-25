{% include-markdown "it/dbzero/magazzino/manual/note_rettifica_riga.md" %}
# 📚 Tabella `note_rettifica_riga`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| target_tipo | character varying(50) | NO |  |
| target_id | bigint | NO |  |
| target_riga_id | bigint | YES |  |
| anchor_tipo | character varying(12) | NO |  |
| posizione | character varying(12) | NO |  |
| seq | integer | NO | 10 |
| testo | text | YES |  |
| testo_md | text | YES |  |
| stile | character varying(16) | NO | 'NORMALE'::character varying |
| lingua | character varying(5) | YES |  |
| visibile | boolean | NO | true |
| solo_stampa | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_lingua_non_vuota |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_rettifica_riga_anchor |  |
| CHECK | chk_note_seq_pos |  |
| FOREIGN KEY | fk_mag_note_target_tipo | target_tipo |
| FOREIGN KEY | fk_note_rettifica_riga_riga | target_riga_id |
| FOREIGN KEY | fk_note_rettifica_riga_testata | target_id |
| PRIMARY KEY | note_rettifica_riga_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_rettifica_riga_render | `CREATE INDEX ix_note_rettifica_riga_render ON magazzino.note_rettifica_riga USING btree (target_id, anchor_tipo, target_riga_id, posizione, seq) WITH (fillfactor='100', deduplicate_items='true')` |
| note_rettifica_riga_pkey | `CREATE UNIQUE INDEX note_rettifica_riga_pkey ON magazzino.note_rettifica_riga USING btree (target_tipo, id)` |
| note_rettifica_riga_target_tipo_target_id_anchor_tipo_posiz_idx | `CREATE INDEX note_rettifica_riga_target_tipo_target_id_anchor_tipo_posiz_idx ON magazzino.note_rettifica_riga USING btree (target_tipo, target_id, anchor_tipo, posizione, seq) WITH (fillfactor='100', deduplicate_items='true')` |
| note_rettifica_riga_target_tipo_target_id_target_riga_id_an_idx | `CREATE INDEX note_rettifica_riga_target_tipo_target_id_target_riga_id_an_idx ON magazzino.note_rettifica_riga USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_rettifica_riga_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_rettifica_riga_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
