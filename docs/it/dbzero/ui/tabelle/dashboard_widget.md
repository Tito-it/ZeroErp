{% include-markdown "it/dbzero/ui/manual/dashboard_widget.md" %}
# 📚 Tabella `dashboard_widget`

> 📝 **Descrizione**
>
> Composizione dashboard&lt;-&gt;widget: pool candidato per dashboard + ordine di default. Sorgente del catalogo grezzo e del merge widget nuovi nella risoluzione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| dashboard_id | integer | NO |  |
| widget_id | integer | NO |  |
| ordine_default | integer | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ui_dashboard_widget_dashboard_definizione | dashboard_id |
| FOREIGN KEY | fk_ui_dashboard_widget_widget | widget_id |
| PRIMARY KEY | pk_ui_dashboard_widget | dashboard_id, widget_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_dashboard_widget_widget_id | `CREATE INDEX ix_ui_dashboard_widget_widget_id ON ui.dashboard_widget USING btree (widget_id)` |
| pk_ui_dashboard_widget | `CREATE UNIQUE INDEX pk_ui_dashboard_widget ON ui.dashboard_widget USING btree (dashboard_id, widget_id)` |

---
{% include-markdown "signature-core.md" %}
