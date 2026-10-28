{% include-markdown "it/dbzero/catalogo/manual/note_articoli_componenti.md" %}
# 📚 Tabella `note_articoli_componenti`

> 📝 **Descrizione**
>
> Partizione note per catalogo.articoli_componenti.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| target_tipo | character varying(50) | NO |  |
| target_id | uuid | NO |  |
| target_riga_id | uuid | YES |  |
| anchor_tipo | character varying(12) | NO |  |
| posizione | character varying(12) | NO |  |
| seq | integer | NO | 10 |
| testo | text | YES |  |
| testo_md | text | YES |  |
| id_stile | bigint | NO |  |
| id_lingua | bigint | YES |  |
| visibile | boolean | NO | true |
| solo_stampa | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_note_anchor_tipo |  |
| CHECK | chk_note_posizione |  |
| CHECK | chk_note_seq_pos |  |
| FOREIGN KEY | fk_cat_note_articoli_componenti_target | target_id |
| FOREIGN KEY | fk_cat_note_id_lingua | id_lingua |
| FOREIGN KEY | fk_cat_note_id_stile | id_stile |
| FOREIGN KEY | fk_cat_note_target_tipo | target_tipo |
| PRIMARY KEY | note_articoli_componenti_pkey | target_tipo, id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| note_articoli_componenti_pkey | `CREATE UNIQUE INDEX note_articoli_componenti_pkey ON catalogo.note_articoli_componenti USING btree (target_tipo, id)` |
| note_articoli_componenti_target_tipo_target_id_anchor_tipo__idx | `CREATE INDEX note_articoli_componenti_target_tipo_target_id_anchor_tipo__idx ON catalogo.note_articoli_componenti USING btree (target_tipo, target_id, anchor_tipo, posizione, seq)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_articoli_componenti_a10_articoli_componenti_req_eb4cdc | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli_componenti', 'attivo', 'target_id', 'id')` |
| trg_note_articoli_componenti_a10_articoli_componenti_req_eb4cdc | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli_componenti', 'attivo', 'target_id', 'id')` |
| trg_note_articoli_componenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_articoli_componenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
