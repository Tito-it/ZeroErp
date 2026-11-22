{% include-markdown "it/dbzero/ui/manual/dashboard_widget.md" %}
# 📚 Tabella `dashboard_widget`

> 📝 **Descrizione**
>
> Il pool di una dashboard: i widget del catalogo globale (ui.widget) che può mostrare, e in che ordine quando nessuno ha scelto. Una riga per dashboard e widget. Un widget fuori dal pool non compare, anche se una preferenza o un preset lo nominano. È una parte della dashboard, senza attivo né audit. La scrive il seed; l'applicazione la legge.

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

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_dashboard_widget_a10_guard_in_uso_dlt | BEFORE | DELETE | `EXECUTE FUNCTION ui.trgfn_ui_dashboard_widget_guard_in_uso()` |

---
{% include-markdown "signature-core.md" %}
