{% include-markdown "it/dbzero/ui/manual/dashboard_preset_widget.md" %}
# 📚 Tabella `dashboard_preset_widget`

> 📝 **Descrizione**
>
> Widget di un preset dashboard: ordine e visibilita di default. Ricalca ui.lista_preset_colonna.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| preset_id | integer | NO |  |
| widget_id | integer | NO |  |
| ordine | integer | NO |  |
| visibile | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ui_dashboard_preset_widget_dashboard_preset | preset_id |
| FOREIGN KEY | fk_ui_dashboard_preset_widget_widget | widget_id |
| PRIMARY KEY | pk_ui_dashboard_preset_widget | preset_id, widget_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_dashboard_preset_widget_widget_id | `CREATE INDEX ix_ui_dashboard_preset_widget_widget_id ON ui.dashboard_preset_widget USING btree (widget_id)` |
| pk_ui_dashboard_preset_widget | `CREATE UNIQUE INDEX pk_ui_dashboard_preset_widget ON ui.dashboard_preset_widget USING btree (preset_id, widget_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_dashboard_preset_widget_z10_tocca_preset_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION ui.trgfn_preset_riga_tocca_preset('ui.dashboard_preset')` |
| trg_ui_dashboard_preset_widget_z10_tocca_preset_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION ui.trgfn_preset_riga_tocca_preset('ui.dashboard_preset')` |
| trg_ui_dashboard_preset_widget_z10_tocca_preset_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION ui.trgfn_preset_riga_tocca_preset('ui.dashboard_preset')` |

---
{% include-markdown "signature-core.md" %}
