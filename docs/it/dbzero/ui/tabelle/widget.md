{% include-markdown "it/dbzero/ui/manual/widget.md" %}
# 📚 Tabella `widget`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| etichetta | character varying | NO |  |
| etichetta_i18n_key | character varying | YES |  |
| tipo_widget | USER-DEFINED | NO | 'kpi'::ui.tipo_widget |
| deep_link | jsonb | YES |  |
| contatore_key | character varying | YES |  |
| soglia | jsonb | YES |  |
| area_id | integer | YES |  |
| azione_id | integer | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO |  |
| data_update | timestamp without time zone | YES |  |
| user_update | character varying | YES |  |

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

---
{% include-markdown "signature-core.md" %}
