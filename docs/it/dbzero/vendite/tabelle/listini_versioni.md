{% include-markdown "it/dbzero/vendite/manual/listini_versioni.md" %}
# 📚 Tabella `listini_versioni`

> 📝 **Descrizione**
>
> Versioni temporali del listino.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| listino_id | bigint | NO |  |
| codice_versione | character varying(64) | NO |  |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| stato | character varying(16) | NO | 'BOZZA'::character varying |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_versioni_chiusa_con_fine |  |
| CHECK | chk_listini_versioni_stato |  |
| FOREIGN KEY | fk_listini_versioni_listino | listino_id |
| PRIMARY KEY | pk_listini_versioni | id |
| UNIQUE | uq_listini_versioni_listino_codice | listino_id, codice_versione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_listini_versioni_no_overlap | `CREATE INDEX ex_listini_versioni_no_overlap ON vendite.listini_versioni USING gist (listino_id, validita) WHERE ((attivo IS TRUE) AND ((stato)::text = ANY (ARRAY['ATTIVA'::text, 'CHIUSA'::text])))` |
| ix_listini_versioni_listino_valido_dal | `CREATE INDEX ix_listini_versioni_listino_valido_dal ON vendite.listini_versioni USING btree (listino_id, valido_dal)` |
| pk_listini_versioni | `CREATE UNIQUE INDEX pk_listini_versioni ON vendite.listini_versioni USING btree (id)` |
| uq_listini_versioni_listino_codice | `CREATE UNIQUE INDEX uq_listini_versioni_listino_codice ON vendite.listini_versioni USING btree (listino_id, codice_versione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_versioni_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'listino_versione_id', 'id', 'attivo')` |
| trg_listini_versioni_a10_contratti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti', 'listino_versione_id', 'id', 'attivo')` |
| trg_listini_versioni_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_listini_versioni_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_listini_versioni_a10_guard_date_chiusa_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_listini_versioni_guard_date_chiusa()` |
| trg_listini_versioni_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('listino', 'listino_id')` |
| trg_listini_versioni_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('listino', 'listino_id')` |
| trg_listini_versioni_a10_guard_transizione_stato_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_listini_versioni_guard_transizione_stato()` |
| trg_listini_versioni_a10_listini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_listini_versioni_a10_listini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_listini_versioni_a10_listini_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe', 'listino_versione_id', 'id', 'attivo')` |
| trg_listini_versioni_a10_listini_righe_componenti_block__758265 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_righe_componenti', 'listino_versione_id', 'id', 'attivo')` |
| trg_listini_versioni_a10_offerte_commerciali_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali', 'listino_versione_id', 'id', 'attivo')` |
| trg_listini_versioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_versioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_versioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_versioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
