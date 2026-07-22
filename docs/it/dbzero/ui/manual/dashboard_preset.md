## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preset`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione)
> [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget)
> [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente)
>
> Funzione:
>
> [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config)

La tabella **`ui.dashboard_preset`** contiene i **default per ambito** di una dashboard, a tre livelli. Ricalca [ui.lista_preset](/dbzero/ui/tabelle/lista_preset), riusando l'ENUM `ui.ambito_preset`.

---

### 🎯 Scopo Principale

* **Default per ambito**:
  * `sistema` → default globale per tutti
  * `emittente_fiscale` → override per una specifica società/emittente
  * `ruolo` → override per un profilo di accesso (`config.profili_accesso`)
* «Chi lavora le pratiche non vede le stesse card di chi fattura» (brief §1) è esattamente l'ambito `ruolo`. La risoluzione usa `script.fn_get_profili_accesso_applicabili` con la `priorita` a rompere i pareggi (AD_HOC prio 1 prevale su REPARTO/PORTALE prio 2).
* **`dimensione_max`**: massimo numero di card mostrabili in dashboard, mirror di `lista_preset.pagina_dimensione`. Se il layout ha un massimo, è un dato sul preset — non implicito nel CSS del frontend. Il seed del preset di sistema è 8.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `dashboard_id` | FK `ui.dashboard_definizione` |
| `ambito` | ENUM `ui.ambito_preset`: `sistema` / `emittente_fiscale` / `ruolo` |
| `profilo_accesso_id` | FK `config.profili_accesso`, valorizzato quando `ambito='ruolo'` |
| `emittente_fiscale_id` | FK `anagrafiche.emittenti_fiscali`, valorizzato quando `ambito='emittente_fiscale'` |
| `is_default` | Preset di default per la combinazione (dashboard, ambito, profilo, emittente) |
| `dimensione_max` | Numero massimo di card (default 8) |

---

### Vincoli

* **CHECK `chk_ui_dashboard_preset_ambito_refs`**: coerenza ambito↔riferimenti (sistema senza refs; ruolo con solo profilo; emittente con solo emittente).
* **UNIQUE parziale `uq_ui_dashboard_preset_default`** su `(dashboard_id, ambito, COALESCE(profilo,0), COALESCE(emittente,0)) WHERE is_default = TRUE`: un solo preset di default per combinazione.

---

### Note operative

* I widget di un preset devono appartenere al pool della dashboard del preset (`ui.dashboard_widget`) — vincolo di seed, non strutturale: `dashboard_preset_widget.widget_id` è FK al catalogo globale, non al pool.
* Un preset senza widget attivi produce un candidato NULL → la risoluzione scende al livello successivo della cascata (stesso comportamento delle liste).
