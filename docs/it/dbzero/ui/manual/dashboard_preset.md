## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preset`

> **Ultimo aggiornamento**: 1 novembre 2026

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
* La cascata è **per chiave** (dal 1-11-2026): il preset di base dà `widget` e `dimensione_max` alle chiavi che la preferenza non ha (vedi [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config)).
* ⭐ **`data_update` è la data dell'ultimo cambio del contenuto**, quella che il flag `preset_aggiornato` confronta con lo snapshot della preferenza. La scrivono `trg_ui_dashboard_preset_a20_data_update_contenuto_upd` (quando cambia `dimensione_max`) e `trg_ui_dashboard_preset_widget_z10_tocca_preset_ins_upd_dlt` (quando un widget del preset si aggiunge, si toglie o cambia), sulle due funzioni condivise con i preset di lista ([`ui.trgfn_preset_data_update_contenuto`](/dbzero/ui/funzioni/trgfn_preset_data_update_contenuto), [`ui.trgfn_preset_riga_tocca_preset`](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset)). Una riscrittura uguale (il seed `loadUpdateData`) non sposta la data. Il perché, per esteso, in [ui.lista_preset](/dbzero/ui/tabelle/lista_preset).
