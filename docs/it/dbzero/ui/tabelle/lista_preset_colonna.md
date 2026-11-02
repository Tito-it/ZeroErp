{% include-markdown "it/dbzero/ui/manual/lista_preset_colonna.md" %}
# 📚 Tabella `lista_preset_colonna`

> 📝 **Descrizione**
>
> Colonne di un preset: ordine, larghezza, visibilita di default e freeze.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| preset_id | integer | NO |  |
| colonna_id | integer | NO |  |
| ordine | integer | NO |  |
| larghezza | integer | YES |  |
| visibile | boolean | NO | true |
| fissata | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_lista_preset_colonna_lista_colonna | colonna_id |
| FOREIGN KEY | fk_lista_preset_colonna_lista_preset | preset_id |
| PRIMARY KEY | pk_ui_lista_preset_colonna | preset_id, colonna_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_lista_preset_colonna_colonna_id | `CREATE INDEX ix_ui_lista_preset_colonna_colonna_id ON ui.lista_preset_colonna USING btree (colonna_id)` |
| pk_ui_lista_preset_colonna | `CREATE UNIQUE INDEX pk_ui_lista_preset_colonna ON ui.lista_preset_colonna USING btree (preset_id, colonna_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_lista_preset_colonna_z10_tocca_preset_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION ui.trgfn_preset_riga_tocca_preset('ui.lista_preset')` |
| trg_ui_lista_preset_colonna_z10_tocca_preset_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION ui.trgfn_preset_riga_tocca_preset('ui.lista_preset')` |
| trg_ui_lista_preset_colonna_z10_tocca_preset_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION ui.trgfn_preset_riga_tocca_preset('ui.lista_preset')` |

---
{% include-markdown "signature-core.md" %}
