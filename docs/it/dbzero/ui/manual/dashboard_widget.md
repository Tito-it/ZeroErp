## 📘 Documentazione Concettuale – Tabella `ui.dashboard_widget`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione)
> [ui.widget](/dbzero/ui/tabelle/widget)
>
> Funzione:
>
> [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config)

La tabella **`ui.dashboard_widget`** è la **composizione dashboard↔widget**: il ponte che rende il widget globale ([ui.widget](/dbzero/ui/tabelle/widget)) utilizzabile su più dashboard senza duplicarne la definizione. Dichiara quali widget del catalogo globale sono candidati per una dashboard e il loro ordine di default.

---

### 🎯 Scopo Principale

* **Pool candidato per dashboard**: elenca i widget disponibili per una dashboard specifica. È anche la sorgente del **"catalogo grezzo"** (fallback "mai vuota") e del **merge automatico** dei widget nuovi nella funzione di risoluzione.
* **Ordine di default**: `ordine_default` determina la disposizione delle card quando manca un preset o una preferenza utente.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `dashboard_id` | FK `ui.dashboard_definizione` |
| `widget_id` | FK `ui.widget` (catalogo globale) |
| `ordine_default` | Ordine del widget nella dashboard in assenza di preset/preferenza |

**PK** `(dashboard_id, widget_id)`: un widget compare una sola volta per dashboard. `dashboard_id` è leading, quindi la PK copre già l'accesso per dashboard (nessun indice FK dedicato su `dashboard_id`; l'indice serve solo su `widget_id`).

---

### Note operative

* Aggiungere un widget a una dashboard = inserire una riga qui; il widget deve già esistere in `ui.widget`.
* Rimuovere un widget dal pool di una dashboard (DELETE qui) lo fa sparire dalla risoluzione anche per gli utenti che lo avevano in preferenza (la risoluzione richiede la membership nel pool).
