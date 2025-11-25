{% include-markdown "it/dbzero/vendite/manual/note_attivita_fatturabili.md" %}
# 📚 Tabella `note_attivita_fatturabili`

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
| CHECK | chk_ven_note_att_anchor |  |
| FOREIGN KEY | fk_ven_note_att_riga | target_riga_id |
| FOREIGN KEY | fk_ven_note_att_testata | target_id |
| FOREIGN KEY | fk_vendite_note_id_lingua | id_lingua, id_lingua, id_lingua, id_lingua, id_lingua, id_lingua, id_lingua |
| FOREIGN KEY | fk_vendite_note_id_stile | id_stile, id_stile, id_stile, id_stile, id_stile, id_stile, id_stile |
| PRIMARY KEY | note_attivita_fatturabili_pkey | id, target_tipo |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ven_note_att_render | `CREATE INDEX ix_ven_note_att_render ON vendite.note_attivita_fatturabili USING btree (target_id, anchor_tipo, target_riga_id, posizione, seq)` |
| note_attivita_fatturabili_pkey | `CREATE UNIQUE INDEX note_attivita_fatturabili_pkey ON vendite.note_attivita_fatturabili USING btree (target_tipo, id)` |
| note_attivita_fatturabili_target_tipo_target_id_anchor_tipo_idx | `CREATE INDEX note_attivita_fatturabili_target_tipo_target_id_anchor_tipo_idx ON vendite.note_attivita_fatturabili USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| note_attivita_fatturabili_target_tipo_target_id_target_riga_idx | `CREATE INDEX note_attivita_fatturabili_target_tipo_target_id_target_riga_idx ON vendite.note_attivita_fatturabili USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |

---
{% include-markdown "signature-core.md" %}
