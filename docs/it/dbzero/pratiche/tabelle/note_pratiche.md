{% include-markdown "it/dbzero/pratiche/manual/note_pratiche.md" %}
# 📚 Tabella `note_pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| tipo_nota_id | integer | NO |  |
| contenuto | text | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_note_pratiche_pratica | pratica_id |
| FOREIGN KEY | fk_note_pratiche_tipo_nota | tipo_nota_id |
| PRIMARY KEY | pk_pratiche_note_pratiche | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_note_pratiche | `CREATE UNIQUE INDEX pk_pratiche_note_pratiche ON pratiche.note_pratiche USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_pratiche_a10_tipi_nota_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_nota', 'attivo', 'tipo_nota_id', 'id')` |
| trg_note_pratiche_a10_tipi_nota_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_nota', 'attivo', 'tipo_nota_id', 'id')` |
| trg_note_pratiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_pratiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_pratiche_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_pratiche_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_pratiche_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_note_pratiche_giornale()` |
| trg_note_pratiche_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('note_pratiche_id')` |
| trg_note_pratiche_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('note_pratiche_id')` |

---
{% include-markdown "signature-core.md" %}
