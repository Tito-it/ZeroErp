{% include-markdown "it/dbzero/config/manual/area_model_overrides.md" %}
# 📚 Tabella `area_model_overrides`

> 📝 **Descrizione**
>
> Override opzionale: riassegna un model Django a un'area funzionale
>  diversa dal suo schema DB. Eccezione rara — il caso standard
>  e' area = schema (risoluzione automatica).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| app_label | character varying | NO |  |
| model_name | character varying | NO |  |
| area_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_area_model_overrides_aree_funzionali | area_id |
| PRIMARY KEY | pk_area_model_overrides | id |
| UNIQUE | uq_area_model_overrides_app_model | app_label, model_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_area_model_overrides_area_id | `CREATE INDEX ix_area_model_overrides_area_id ON config.area_model_overrides USING btree (area_id)` |
| pk_area_model_overrides | `CREATE UNIQUE INDEX pk_area_model_overrides ON config.area_model_overrides USING btree (id)` |
| uq_area_model_overrides_app_model | `CREATE UNIQUE INDEX uq_area_model_overrides_app_model ON config.area_model_overrides USING btree (app_label, model_name)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_area_model_overrides_a10_aree_funzionali_require_att_987255 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_area_model_overrides_a10_aree_funzionali_require_att_987255 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_area_model_overrides_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_area_model_overrides_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
