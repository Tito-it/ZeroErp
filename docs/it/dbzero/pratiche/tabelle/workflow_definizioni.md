{% include-markdown "it/dbzero/pratiche/manual/workflow_definizioni.md" %}
# 📚 Tabella `workflow_definizioni`

> 📝 **Descrizione**
>
> Edizioni versionate delle definizioni di workflow (modello C «edizioni + fork»). Una riga = una edizione per (tipo_prestazione, scope); emittente_fiscale_id NULL = preset. Ciclo: BOZZA -&gt; PUBBLICATA (unica per scope, immutabile da Fase 1) -&gt; RITIRATA. Le pratiche pinnano la definizione alla creazione (pratiche.definizione_id) e la tengono per sempre.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| tipo_prestazione_id | integer | NO |  |
| emittente_fiscale_id | bigint | YES |  |
| versione | integer | NO | 1 |
| stato | character varying(20) | NO | 'BOZZA'::character varying |
| preset_origine_id | integer | YES |  |
| versione_origine | integer | YES |  |
| descrizione | text | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_workflow_definizioni_stato |  |
| CHECK | chk_workflow_definizioni_versione |  |
| FOREIGN KEY | fk_workflow_definizioni_emittente | emittente_fiscale_id |
| FOREIGN KEY | fk_workflow_definizioni_preset_origine | preset_origine_id |
| FOREIGN KEY | fk_workflow_definizioni_tipo_prestazione | tipo_prestazione_id |
| PRIMARY KEY | pk_pratiche_workflow_definizioni | id |
| UNIQUE | uq_workflow_definizioni_id_tipo | id, tipo_prestazione_id |
| UNIQUE | uq_workflow_definizioni_scope_versione | tipo_prestazione_id, emittente_fiscale_id, versione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_workflow_definizioni | `CREATE UNIQUE INDEX pk_pratiche_workflow_definizioni ON pratiche.workflow_definizioni USING btree (id)` |
| uq_workflow_definizioni_bozza | `CREATE UNIQUE INDEX uq_workflow_definizioni_bozza ON pratiche.workflow_definizioni USING btree (tipo_prestazione_id, emittente_fiscale_id) NULLS NOT DISTINCT WHERE ((stato)::text = 'BOZZA'::text)` |
| uq_workflow_definizioni_id_tipo | `CREATE UNIQUE INDEX uq_workflow_definizioni_id_tipo ON pratiche.workflow_definizioni USING btree (id, tipo_prestazione_id)` |
| uq_workflow_definizioni_pubblicata | `CREATE UNIQUE INDEX uq_workflow_definizioni_pubblicata ON pratiche.workflow_definizioni USING btree (tipo_prestazione_id, emittente_fiscale_id) NULLS NOT DISTINCT WHERE ((stato)::text = 'PUBBLICATA'::text)` |
| uq_workflow_definizioni_scope_versione | `CREATE UNIQUE INDEX uq_workflow_definizioni_scope_versione ON pratiche.workflow_definizioni USING btree (tipo_prestazione_id, emittente_fiscale_id, versione) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_workflow_definizioni_a10_emittenti_fiscali_require_a_279281 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_workflow_definizioni_a10_emittenti_fiscali_require_a_279281 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_fiscale_id', 'id')` |
| trg_workflow_definizioni_a10_guard_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_workflow_definizioni_guard()` |
| trg_workflow_definizioni_a10_tipi_prestazione_require_at_697860 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_workflow_definizioni_a10_tipi_prestazione_require_at_697860 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_workflow_definizioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_workflow_definizioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_workflow_definizioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_workflow_definizioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
