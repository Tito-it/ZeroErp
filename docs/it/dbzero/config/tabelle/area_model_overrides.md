{% include-markdown "it/dbzero/config/manual/area_model_overrides.md" %}
# 📚 Tabella `area_model_overrides`

> 📝 **Descrizione**
>
> Catalogo degli oggetti (app_label, model_name) che il pannello dei permessi conosce. Per ognuno: l'area a cui appartiene (script.fn_area_di_oggetto; un oggetto non a catalogo vale come area = app_label) e se si puo' personalizzare per operatore (riservato = false). Un override in config.user_override_oggetti esiste solo per un oggetto a catalogo e non riservato (FK composita). Seed: CSV 80_data/sql/config/area_model_overrides.csv. Brief: brief-db-be-fe-catalogo-oggetti-permessi (2026-09-28).

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
| riservato | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_area_model_overrides_aree_funzionali | area_id |
| PRIMARY KEY | pk_area_model_overrides | id |
| UNIQUE | uq_area_model_overrides_app_model | app_label, model_name |
| UNIQUE | uq_area_model_overrides_app_model_riservato | app_label, model_name, riservato |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_area_model_overrides_area_id | `CREATE INDEX ix_area_model_overrides_area_id ON config.area_model_overrides USING btree (area_id)` |
| pk_area_model_overrides | `CREATE UNIQUE INDEX pk_area_model_overrides ON config.area_model_overrides USING btree (id)` |
| uq_area_model_overrides_app_model | `CREATE UNIQUE INDEX uq_area_model_overrides_app_model ON config.area_model_overrides USING btree (app_label, model_name)` |
| uq_area_model_overrides_app_model_riservato | `CREATE UNIQUE INDEX uq_area_model_overrides_app_model_riservato ON config.area_model_overrides USING btree (app_label, model_name, riservato)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_area_model_overrides_a10_aree_funzionali_require_att_987255 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_area_model_overrides_a10_aree_funzionali_require_att_987255 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_area_model_overrides_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_area_model_overrides_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
