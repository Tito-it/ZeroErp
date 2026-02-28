# 📚 Tabella `note_asset`

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
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_asset_anchor |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| CHECK | chk_note_target_tipo |  |
| FOREIGN KEY | fk_note_asset_testata | target_id |
| PRIMARY KEY | note_asset_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_asset_render | `CREATE INDEX ix_note_asset_render ON magazzino.note_asset USING btree (target_id, anchor_tipo, posizione, seq) WITH (fillfactor='100', deduplicate_items='true')` |
| note_asset_pkey | `CREATE UNIQUE INDEX note_asset_pkey ON magazzino.note_asset USING btree (target_tipo, id)` |
| note_asset_target_tipo_target_id_anchor_tipo_posizione_seq_idx | `CREATE INDEX note_asset_target_tipo_target_id_anchor_tipo_posizione_seq_idx ON magazzino.note_asset USING btree (target_tipo, target_id, anchor_tipo, posizione, seq) WITH (fillfactor='100', deduplicate_items='true')` |
| note_asset_target_tipo_target_id_target_riga_id_anchor_tipo_idx | `CREATE INDEX note_asset_target_tipo_target_id_target_riga_id_anchor_tipo_idx ON magazzino.note_asset USING btree (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, seq) WHERE (target_riga_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_asset_a10_assets_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'target_id')` |
| trg_note_asset_a10_assets_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'assets', 'attivo', 'target_id')` |
| trg_note_asset_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_asset_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
