## 📘 Documentazione Concettuale – Tabella `ui.lista_preset_colonna`

> 👀 **Vedi anche**
>
> [ui.lista_preset](/dbzero/ui/tabelle/lista_preset)
> [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna)

La tabella **`ui.lista_preset_colonna`** definisce la **composizione di un preset**: quali colonne include, in che ordine, con che larghezza e con quale visibilità di default.

---

### 🎯 Scopo Principale

* **Composizione del preset**: ogni riga indica che la colonna `colonna_id` fa parte del preset `preset_id`, con il proprio ordinamento e larghezza personalizzata.
* **Pool disponibile vs visibile di default**: `visibile = FALSE` significa che la colonna è nel pool (appare nella modale di personalizzazione come selezionabile) ma non è mostrata nella lista di default. Permette preset con 30 colonne nel pool ma solo 8 visibili.
* **Colonne fissate**: `fissata = TRUE` indica colonne frozen (non scorrono orizzontalmente). Tipico per la colonna identificatore o nome.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `ordine` | Posizione nella lista; usato per `ORDER BY` nell'output JSONB |
| `larghezza` | Override in pixel della larghezza default del catalogo. `NULL` = usa `lista_colonna.larghezza_default` |
| `visibile` | `FALSE`: colonna disponibile ma non mostrata di default |
| `fissata` | `TRUE`: colonna frozen (non scorre orizzontalmente) |

---

### Note operative

* La PK composita `(preset_id, colonna_id)` garantisce che ogni colonna compaia al massimo una volta per preset.
* La FK su `lista_preset` è `ON DELETE CASCADE`: eliminare un preset rimuove automaticamente tutte le sue colonne.
* Non ci sono campi audit (nessun `data_insert`/`user_insert`): la tracciabilità è delegata al preset padre.
