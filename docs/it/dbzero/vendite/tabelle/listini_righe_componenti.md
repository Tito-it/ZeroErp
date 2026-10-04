{% include-markdown "it/dbzero/vendite/manual/listini_righe_componenti.md" %}
# 📚 Tabella `listini_righe_componenti`

> 📝 **Descrizione**
>
> Prezzi bundle per componenti BoM in contesto versione listino. Una riga = prezzo del componente X del padre Y nella versione V. Immutabile quando versione ATTIVA (guard 20260513-20). Prezzo padre composito = SUM(componenti). rev 2026-05-13.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| listino_versione_id | bigint | NO |  |
| articolo_componente_id | uuid | NO |  |
| articolo_padre_id | uuid | NO |  |
| articolo_figlio_id | uuid | NO |  |
| prezzo | numeric(18,6) | NO |  |
| iva_id | bigint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | NO | now() |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listrighe_comp_prezzo_notnull |  |
| FOREIGN KEY | fk_listrighe_comp_articoli_comp_temporal | articolo_componente_id, validita |
| FOREIGN KEY | listini_righe_componenti_articolo_componente_id_fkey | articolo_componente_id |
| FOREIGN KEY | listini_righe_componenti_articolo_figlio_id_fkey | articolo_figlio_id |
| FOREIGN KEY | listini_righe_componenti_articolo_padre_id_fkey | articolo_padre_id |
| FOREIGN KEY | listini_righe_componenti_iva_id_fkey | iva_id |
| FOREIGN KEY | listini_righe_componenti_listino_versione_id_fkey | listino_versione_id |
| PRIMARY KEY | listini_righe_componenti_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_listini_righe_comp_no_overlap | `CREATE INDEX ex_listini_righe_comp_no_overlap ON vendite.listini_righe_componenti USING gist (listino_versione_id, articolo_componente_id, validita) WHERE (attivo = true)` |
| ix_listini_righe_comp_padre_data | `CREATE INDEX ix_listini_righe_comp_padre_data ON vendite.listini_righe_componenti USING btree (articolo_padre_id, listino_versione_id) WHERE (attivo = true)` |
| listini_righe_componenti_pkey | `CREATE UNIQUE INDEX listini_righe_componenti_pkey ON vendite.listini_righe_componenti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_righe_componenti_a10_articoli_componenti_req_1f9d45 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli_componenti', 'attivo', 'articolo_componente_id', 'id')` |
| trg_listini_righe_componenti_a10_articoli_componenti_req_1f9d45 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli_componenti', 'attivo', 'articolo_componente_id', 'id')` |
| trg_listini_righe_componenti_a10_articoli_require_attivo_7576e7 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_figlio_id', 'id')` |
| trg_listini_righe_componenti_a10_articoli_require_attivo_7576e7 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_figlio_id', 'id')` |
| trg_listini_righe_componenti_a10_articoli_require_attivo_dcaf93 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_padre_id', 'id')` |
| trg_listini_righe_componenti_a10_articoli_require_attivo_dcaf93 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_padre_id', 'id')` |
| trg_listini_righe_componenti_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_listini_righe_componenti_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_listini_righe_componenti_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_listini_righe_componenti_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_listini_righe_componenti_a10_listini_versioni_requir_65ed90 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_listini_righe_componenti_a10_listini_versioni_requir_65ed90 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini_versioni', 'attivo', 'listino_versione_id', 'id')` |
| trg_listrighe_comp_a10_guard_coerenza_bom_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()` |
| trg_listrighe_comp_a10_guard_coerenza_bom_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()` |
| trg_listrighe_comp_a10_guard_immutabilita_v5_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()` |
| trg_listrighe_comp_a10_guard_immutabilita_v5_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()` |
| trg_listrighe_comp_a10_guard_immutabilita_v5_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()` |
| trg_listrighe_comp_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listrighe_comp_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listrighe_comp_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listrighe_comp_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
