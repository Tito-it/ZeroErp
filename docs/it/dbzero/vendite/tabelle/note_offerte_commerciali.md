{% include-markdown "it/dbzero/vendite/manual/note_offerte_commerciali.md" %}
# 📚 Tabella `note_offerte_commerciali`

> 📝 **Descrizione**
>
> Partizione note per vendite.offerte_commerciali. Supporta ancoraggio DOCUMENTO (nota testata offerta) e RIGA (nota su singola eccezione offerte_commerciali_eccezioni). Pattern identico a note_contratto. FK target_riga_id -&gt; offerte_commerciali_eccezioni aggiunta in 20260524-09. rev 2026-05-24.

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
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| CHECK | chk_note_testo_non_vuoto |  |
| CHECK | chk_offnote_anchor |  |
| FOREIGN KEY | fk_offnote_riga | target_riga_id |
| FOREIGN KEY | fk_offnote_testata | target_id |
| FOREIGN KEY | fk_vendite_note_id_lingua | id_lingua |
| FOREIGN KEY | fk_vendite_note_id_stile | id_stile |
| FOREIGN KEY | fk_vendite_note_target_tipo | target_tipo |
| PRIMARY KEY | note_offerte_commerciali_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_offnote_render | `CREATE INDEX ix_offnote_render ON vendite.note_offerte_commerciali USING btree (target_id, anchor_tipo, target_riga_id, posizione, seq)` |
| note_offerte_commerciali_pkey | `CREATE UNIQUE INDEX note_offerte_commerciali_pkey ON vendite.note_offerte_commerciali USING btree (target_tipo, id)` |
| note_offerte_commerciali_target_tipo_target_id_anchor_tipo__idx | `CREATE INDEX note_offerte_commerciali_target_tipo_target_id_anchor_tipo__idx ON vendite.note_offerte_commerciali USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| note_offerte_commerciali_target_tipo_target_id_target_riga__idx | `CREATE INDEX note_offerte_commerciali_target_tipo_target_id_target_riga__idx ON vendite.note_offerte_commerciali USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_offerte_commerciali_a10_offerte_commerciali_ecc_499d43 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'offerte_commerciali_eccezioni', 'attivo', 'target_riga_id', 'id')` |
| trg_note_offerte_commerciali_a10_offerte_commerciali_ecc_499d43 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'offerte_commerciali_eccezioni', 'attivo', 'target_riga_id', 'id')` |
| trg_note_offerte_commerciali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_offerte_commerciali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_offerte_commerciali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_offerte_commerciali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_offerte_commerciali_validate_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_note_validate_generic('vendite.offerte_commerciali_eccezioni', 'offerta_id')` |
| trg_note_offerte_commerciali_validate_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_note_validate_generic('vendite.offerte_commerciali_eccezioni', 'offerta_id')` |

---
{% include-markdown "signature-core.md" %}
