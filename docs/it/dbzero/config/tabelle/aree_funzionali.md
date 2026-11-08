{% include-markdown "it/dbzero/config/manual/aree_funzionali.md" %}
# 📚 Tabella `aree_funzionali`

> 📝 **Descrizione**
>
> Catalogo delle aree funzionali del sistema permessi: l'unità a cui si concede un livello (BLOCCATO, LETTURA, TUTTO) nei profili di accesso e negli override utente. L'area si identifica con schema_db, la sua chiave tecnica, uguale a codice; codice_interno è il codice immutabile. Il backend ricava l'area di un endpoint dal db_table del model o, quando la view non ne ha uno, dal suo attributo area_funzionale: un'area non ha bisogno di uno schema fisico omonimo. Piano: brief-db-area-funzionale-assistente-ai, §4.1.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | character varying(200) | NO |  |
| schema_db | character varying(50) | NO |  |
| attivo | boolean | NO | true |
| ordinamento | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_aree_funzionali | id |
| UNIQUE | uq_aree_funzionali_codice | codice |
| UNIQUE | uq_aree_funzionali_codice_interno | codice_interno |
| UNIQUE | uq_aree_funzionali_schema_db | schema_db |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_aree_funzionali | `CREATE UNIQUE INDEX pk_aree_funzionali ON config.aree_funzionali USING btree (id)` |
| uq_aree_funzionali_codice | `CREATE UNIQUE INDEX uq_aree_funzionali_codice ON config.aree_funzionali USING btree (codice)` |
| uq_aree_funzionali_codice_interno | `CREATE UNIQUE INDEX uq_aree_funzionali_codice_interno ON config.aree_funzionali USING btree (codice_interno)` |
| uq_aree_funzionali_schema_db | `CREATE UNIQUE INDEX uq_aree_funzionali_schema_db ON config.aree_funzionali USING btree (schema_db)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_aree_funzionali_a10_area_model_overrides_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'area_model_overrides', 'area_id', 'id', 'attivo')` |
| trg_aree_funzionali_a10_azioni_processo_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'azioni_processo', 'area_id', 'id', 'attivo')` |
| trg_aree_funzionali_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_aree_funzionali_a10_profili_accesso_aree_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'profili_accesso_aree', 'area_id', 'id', 'attivo')` |
| trg_aree_funzionali_a10_user_override_aree_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'user_override_aree', 'area_id', 'id', 'attivo')` |
| trg_aree_funzionali_a10_widget_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('ui', 'widget', 'area_id', 'id', 'attivo')` |
| trg_aree_funzionali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_aree_funzionali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_aree_funzionali_z90_notify_permessi_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_aree_funzionali_z90_notify_permessi_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_aree_funzionali_z90_notify_permessi_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |

---
{% include-markdown "signature-core.md" %}
