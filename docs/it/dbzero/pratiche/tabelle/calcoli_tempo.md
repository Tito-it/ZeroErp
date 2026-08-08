{% include-markdown "it/dbzero/pratiche/manual/calcoli_tempo.md" %}
# 📚 Tabella `calcoli_tempo`

> 📝 **Descrizione**
>
> Calcolo persistente tempi da/a tra flussi.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| flusso_da_id | bigint | NO |  |
| flusso_a_id | bigint | NO |  |
| formula_tempo_id | integer | NO |  |
| data_inizio_calcolo | timestamp with time zone | NO |  |
| data_fine_calcolo | timestamp with time zone | YES |  |
| giorni_lordi | integer | YES |  |
| giorni_sospensione | integer | YES |  |
| giorni_netti | integer | YES |  |
| giorni_formula | integer | NO |  |
| sforato | boolean | YES |  |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| periodo_calcolo | tstzrange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_calcoli_tempo_da_diverso_a |  |
| CHECK | chk_calcoli_tempo_data_fine |  |
| CHECK | chk_calcoli_tempo_giorni_formula |  |
| FOREIGN KEY | fk_calcoli_tempo_flusso_a | flusso_a_id |
| FOREIGN KEY | fk_calcoli_tempo_flusso_da | flusso_da_id |
| FOREIGN KEY | fk_calcoli_tempo_formula | formula_tempo_id |
| FOREIGN KEY | fk_calcoli_tempo_pratica | pratica_id |
| PRIMARY KEY | pk_pratiche_calcoli_tempo | id |
| UNIQUE | uq_calcoli_tempo_pratica_da_a_formula | pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_calcoli_tempo | `CREATE UNIQUE INDEX pk_pratiche_calcoli_tempo ON pratiche.calcoli_tempo USING btree (id)` |
| uq_calcoli_tempo_pratica_da_a_formula | `CREATE UNIQUE INDEX uq_calcoli_tempo_pratica_da_a_formula ON pratiche.calcoli_tempo USING btree (pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_calcoli_tempo_a10_formule_tempo_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'formule_tempo', 'attivo', 'formula_tempo_id', 'id')` |
| trg_calcoli_tempo_a10_formule_tempo_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'formule_tempo', 'attivo', 'formula_tempo_id', 'id')` |
| trg_calcoli_tempo_a10_guard_immutabili_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_calcoli_tempo_guard_immutabili()` |
| trg_calcoli_tempo_a20_set_periodo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_calcoli_tempo_set_periodo()` |
| trg_calcoli_tempo_a20_set_periodo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_calcoli_tempo_set_periodo()` |
| trg_calcoli_tempo_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_calcoli_tempo_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_calcoli_tempo_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_calcoli_tempo_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
