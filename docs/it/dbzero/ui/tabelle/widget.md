{% include-markdown "it/dbzero/ui/manual/widget.md" %}
# 📚 Tabella `widget`

> 📝 **Descrizione**
>
> Catalogo GLOBALE dei widget dashboard (card KPI). codice unico globale; il legame con le dashboard e in ui.dashboard_widget. Zero logica di business: deep_link/contatore_key/soglia sono opachi al DB.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(80) | NO |  |
| etichetta | character varying(120) | NO |  |
| etichetta_i18n_key | character varying(120) | YES |  |
| tipo_widget | ui.tipo_widget | NO | 'kpi'::ui.tipo_widget |
| deep_link | jsonb | YES |  |
| contatore_key | character varying(120) | YES |  |
| soglia | jsonb | YES |  |
| area_id | integer | YES |  |
| azione_id | integer | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO |  |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ui_widget_aree_funzionali | area_id |
| FOREIGN KEY | fk_ui_widget_azioni_processo | azione_id |
| PRIMARY KEY | widget_pkey | id |
| UNIQUE | uq_ui_widget_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_widget_area_id | `CREATE INDEX ix_ui_widget_area_id ON ui.widget USING btree (area_id) WHERE (area_id IS NOT NULL)` |
| ix_ui_widget_azione_id | `CREATE INDEX ix_ui_widget_azione_id ON ui.widget USING btree (azione_id) WHERE (azione_id IS NOT NULL)` |
| uq_ui_widget_codice | `CREATE UNIQUE INDEX uq_ui_widget_codice ON ui.widget USING btree (codice)` |
| widget_pkey | `CREATE UNIQUE INDEX widget_pkey ON ui.widget USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_widget_a10_aree_funzionali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_widget_a10_aree_funzionali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_widget_a10_azioni_processo_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'azioni_processo', 'attivo', 'azione_id', 'id')` |
| trg_widget_a10_azioni_processo_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'azioni_processo', 'attivo', 'azione_id', 'id')` |
| trg_widget_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_widget_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
