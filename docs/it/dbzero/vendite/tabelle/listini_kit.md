{% include-markdown "it/dbzero/vendite/manual/listini_kit.md" %}
# 📚 Tabella `listini_kit`

> 📝 **Descrizione**
>
> Il KIT su una versione di listino, per cio' che non e' un prezzo: oggi la periodicita' con cui si addebita a canone (D-2-bis, decisione B di Tid, 2026-10-31). Il kit sul listino non ha una riga in vendite.listini_righe (decisione del modello unificato dei componenti, 2026-05): il suo prezzo e' la somma dei componenti (vendite.listini_righe_componenti), e qui non c'e'. Si scrive solo in bozza (vendite.trgfn_listini_kit_guard); la versione clonata la copia, quella eliminata la porta via. La legge vendite.fn_listino_periodicita_articolo, la sede della periodicita' di un articolo sul listino. Brief: brief-db-contratto-righe-periodiche-in-commessa §7.2.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| listino_versione_id | bigint | NO |  |
| articolo_padre_id | uuid | NO |  |
| periodicita | character varying(32) | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_listini_kit_articolo | articolo_padre_id |
| FOREIGN KEY | fk_listini_kit_periodicita | periodicita |
| FOREIGN KEY | fk_listini_kit_versione | listino_versione_id |
| PRIMARY KEY | pk_listini_kit | id |
| UNIQUE | uq_listini_kit_versione_articolo | listino_versione_id, articolo_padre_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini_kit | `CREATE UNIQUE INDEX pk_listini_kit ON vendite.listini_kit USING btree (id)` |
| uq_listini_kit_versione_articolo | `CREATE UNIQUE INDEX uq_listini_kit_versione_articolo ON vendite.listini_kit USING btree (listino_versione_id, articolo_padre_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_kit_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_padre_id', 'id')` |
| trg_listini_kit_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_padre_id', 'id')` |
| trg_listini_kit_a10_guard_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_listini_kit_guard()` |
| trg_listini_kit_a10_guard_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_listini_kit_guard()` |
| trg_listini_kit_a10_guard_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_listini_kit_guard()` |
| trg_listini_kit_a10_listini_versioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_listini_kit_a10_listini_versioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_listini_kit_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('articolo_padre_id', 'E_LISTINO_RIGA_IDENTITA_IMMUTABILE', 'listino_versione_id', 'E_LISTINO_RIGA_IDENTITA_IMMUTABILE')` |
| trg_listini_kit_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_kit_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_kit_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_kit_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
