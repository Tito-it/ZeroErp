{% include-markdown "it/dbzero/ui/manual/lista_preset_colonna.md" %}

# 📚 Tabella `lista_preset_colonna`

## 🗂️ Campi principali

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| preset_id | integer | NO | |
| colonna_id | integer | NO | |
| ordine | integer | NO | |
| larghezza | integer | YES | |
| visibile | boolean | NO | true |
| fissata | boolean | NO | false |

> Tabella tecnica di composizione (join table PK composita). Non ha campi audit né trigger.

## 🔒 Vincoli

| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_ui_lista_preset_colonna | preset_id, colonna_id |
| FOREIGN KEY | fk_lista_preset_colonna_lista_preset | preset_id → ui.lista_preset(id) ON DELETE CASCADE |
| FOREIGN KEY | fk_lista_preset_colonna_lista_colonna | colonna_id → ui.lista_colonna(id) |

## 📑 Indici

| Nome | Definizione |
|------|-------------|
| pk_ui_lista_preset_colonna | `CREATE UNIQUE INDEX ON ui.lista_preset_colonna USING btree (preset_id, colonna_id)` |
| ix_ui_lista_preset_colonna_colonna_id | `CREATE INDEX ON ui.lista_preset_colonna USING btree (colonna_id)` |

---
{% include-markdown "signature-core.md" %}
