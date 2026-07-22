## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preset_widget`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset)
> [ui.widget](/dbzero/ui/tabelle/widget)
>
> Funzione:
>
> [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config)

La tabella **`ui.dashboard_preset_widget`** è la **composizione di un preset dashboard**: quali widget, in che ordine, visibili di default o solo nel pool. Ricalca [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna).

---

### 🎯 Scopo Principale

* **Definisce il contenuto di un preset**: l'insieme dei widget che il preset propone e il loro ordine.
* **`visibile=FALSE`**: il widget è nel **pool** selezionabile (appare nella personalizzazione) ma non è mostrato di default. Consente preset con molti widget disponibili ma poche card visibili di default.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `preset_id` | FK `ui.dashboard_preset` (`ON DELETE CASCADE`) |
| `widget_id` | FK `ui.widget` (catalogo globale) |
| `ordine` | Ordine del widget nel preset |
| `visibile` | `FALSE` = widget nel pool ma non mostrato di default |

**PK** `(preset_id, widget_id)`. `preset_id` è leading, quindi la PK copre l'accesso per preset (indice FK dedicato solo su `widget_id`).

---

### Note operative

* `ON DELETE CASCADE` da `ui.dashboard_preset`: eliminare un preset elimina le sue righe di composizione.
* I widget referenziati devono appartenere al pool della dashboard del preset (`ui.dashboard_widget`): vincolo di seed.
