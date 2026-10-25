{% include-markdown "it/dbzero/vendite/manual/note_fatture.md" %}
# 📚 Tabella `note_fatture`

> 📝 **Descrizione**
>
> Partizione note per fatture (FK forti verso testata/righe FATTURA).

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
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatnote_testo_non_vuoto |  |
| CHECK | chk_fatture_note_anchor |  |
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| CHECK | chk_note_testo_non_vuoto |  |
| FOREIGN KEY | fk_fatture_note_riga | target_riga_id |
| FOREIGN KEY | fk_fatture_note_testata | target_id |
| FOREIGN KEY | fk_vendite_note_id_lingua | id_lingua |
| FOREIGN KEY | fk_vendite_note_id_stile | id_stile |
| FOREIGN KEY | fk_vendite_note_target_tipo | target_tipo |
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
| trg_note_fatture_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_fatture_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_fatture_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_fatture_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_fatture_validate_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_note_validate_generic('vendite.fatture_righe', 'fattura_id')` |
| trg_note_fatture_validate_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_note_validate_generic('vendite.fatture_righe', 'fattura_id')` |

---
{% include-markdown "signature-core.md" %}
