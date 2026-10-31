{% include-markdown "it/dbzero/vendite/manual/listini_righe.md" %}
# 📚 Tabella `listini_righe`

> 📝 **Descrizione**
>
> Prezzi per combinazione dimensionale e versione listino.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| listino_versione_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| uom_id | bigint | NO |  |
| prezzo | numeric(22,10) | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| periodicita | character varying(32) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_righe_prezzo |  |
| CHECK | chk_listini_righe_prezzo_finito |  |
| FOREIGN KEY | fk_listini_righe_articolo | articolo_id |
| FOREIGN KEY | fk_listini_righe_periodicita | periodicita |
| FOREIGN KEY | fk_listini_righe_uom | uom_id |
| FOREIGN KEY | fk_listini_righe_versione | listino_versione_id |
| PRIMARY KEY | pk_listini_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini_righe | `CREATE UNIQUE INDEX pk_listini_righe ON vendite.listini_righe USING btree (id)` |
| uq_listini_righe_key_attiva | `CREATE UNIQUE INDEX uq_listini_righe_key_attiva ON vendite.listini_righe USING btree (listino_versione_id, articolo_id, uom_id) WHERE (attivo IS TRUE)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_listini_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_listini_righe_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'listino_riga_id', 'id', 'attivo')` |
| trg_listini_righe_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'listino_riga_id', 'id', 'attivo')` |
| trg_listini_righe_a10_guard_articolo_ammesso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('LISTINO_VERSIONE', 'listino_versione_id')` |
| trg_listini_righe_a10_guard_articolo_ammesso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('LISTINO_VERSIONE', 'listino_versione_id')` |
| trg_listini_righe_a10_guard_stato_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_listini_righe_guard_stato()` |
| trg_listini_righe_a10_guard_stato_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_listini_righe_guard_stato()` |
| trg_listini_righe_a10_listini_versioni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_listini_righe_a10_listini_versioni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_listini_righe_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('articolo_id', 'E_LISTINO_RIGA_IDENTITA_IMMUTABILE', 'listino_versione_id', 'E_LISTINO_RIGA_IDENTITA_IMMUTABILE', 'uom_id', 'E_LISTINO_RIGA_IDENTITA_IMMUTABILE')` |
| trg_listini_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_listini_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_listini_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
