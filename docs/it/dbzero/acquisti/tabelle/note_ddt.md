{% include-markdown "it/dbzero/acquisti/manual/note_ddt.md" %}
# 📚 Tabella `note_ddt`

> 📝 **Descrizione**
>
> Partizione note per DDT/ricezioni fornitore.

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
| visibile | boolean | NO | true |
| solo_stampa | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| id_stile | bigint | NO |  |
| id_lingua | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_acq_ddt_note_anchor |  |
| CHECK | chk_acq_note_anchor_tipo |  |
| CHECK | chk_acq_note_posizione |  |
| CHECK | chk_acq_note_seq_pos |  |
| CHECK | chk_ddtnote_testo_non_vuoto |  |
| CHECK | chk_note_testo_non_vuoto |  |
| FOREIGN KEY | fk_acq_ddt_note_riga | target_riga_id |
| FOREIGN KEY | fk_acq_ddt_note_testata | target_id |
| FOREIGN KEY | fk_acq_note_id_lingua | id_lingua |
| FOREIGN KEY | fk_acq_note_id_stile | id_stile |
| FOREIGN KEY | fk_acq_note_target_tipo | target_tipo |
| PRIMARY KEY | note_ddt_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_acq_ddt_note_render | `CREATE INDEX ix_acq_ddt_note_render ON acquisti.note_ddt USING btree (target_id, anchor_tipo, target_riga_id, posizione, seq)` |
| note_ddt_pkey | `CREATE UNIQUE INDEX note_ddt_pkey ON acquisti.note_ddt USING btree (target_tipo, id)` |
| note_ddt_target_tipo_target_id_anchor_tipo_posizione_seq_idx | `CREATE INDEX note_ddt_target_tipo_target_id_anchor_tipo_posizione_seq_idx ON acquisti.note_ddt USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| note_ddt_target_tipo_target_id_target_riga_id_anchor_tipo_p_idx | `CREATE INDEX note_ddt_target_tipo_target_id_target_riga_id_anchor_tipo_p_idx ON acquisti.note_ddt USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_ddt_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_ddt_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_ddt_validate_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_note_validate_generic('acquisti.ddt_righe', 'ddt_id')` |
| trg_note_ddt_validate_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_note_validate_generic('acquisti.ddt_righe', 'ddt_id')` |

---
{% include-markdown "signature-core.md" %}
