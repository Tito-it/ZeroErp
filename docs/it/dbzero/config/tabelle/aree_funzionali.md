{% include-markdown "it/dbzero/config/manual/aree_funzionali.md" %}
# 📚 Tabella `aree_funzionali`

> 📝 **Descrizione**
>
> Catalogo aree funzionali del sistema permessi.
>  Ogni area corrisponde a uno schema DB; il mapping area-&gt;schema
>  e' automatico (Django risolve l'area dal db_table del model).
>  schema_db separato da codice per consentire rinomina label
>  senza impatto sullo schema fisico.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO |  |
| schema_db | character varying | NO |  |
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
| trg_aree_funzionali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_aree_funzionali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
