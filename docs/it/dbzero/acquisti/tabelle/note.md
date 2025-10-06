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
| CHECK | chk_acq_note_anchor_tipo |  |
| CHECK | chk_acq_note_posizione |  |
| CHECK | chk_acq_note_seq_pos |  |
| CHECK | chk_acq_note_target_tipo |  |
| PRIMARY KEY | pk_note_acq | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_acq_note_render_order | `CREATE INDEX ix_acq_note_render_order ON ONLY acquisti.note USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |
| ix_acquisti_note_by_riga | `CREATE INDEX ix_acquisti_note_by_riga ON ONLY acquisti.note USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |
| pk_note_acq | `CREATE UNIQUE INDEX pk_note_acq ON ONLY acquisti.note USING btree (target_tipo, id)` |

---
{% include-markdown "signature-core.md" %}
