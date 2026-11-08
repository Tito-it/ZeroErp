## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preferenza_utente`

> **Ultimo aggiornamento**: 8 novembre 2026

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione)
> [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset)
> [ui.widget](/dbzero/ui/tabelle/widget)
>
> Funzione:
>
> [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config)
> [ui.trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts](/dbzero/ui/funzioni/trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts)

La tabella **`ui.dashboard_preferenza_utente`** contiene la **preferenza personale** dell'utente per una dashboard. Un solo record per coppia `(auth_user, dashboard)`. Ricalca [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente).

---

### 🎯 Scopo Principale

* **Override utente, chiave per chiave**: la selezione e l'ordine dei widget scelti dall'utente vincono sul default di ruolo/emittente/sistema. Dal 1-11-2026 la preferenza porta solo le chiavi scelte (`widget`, `dimensione_max`): una chiave assente (o `null`) segue lo standard, e chi salva rimanda solo le chiavi che il resolver dice di `origine` `preferenza`, più quella toccata. Una preferenza senza chiavi si cancella (vuota, lo snapshot del preset accenderebbe il banner senza niente da riconciliare). Vedi [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config).
* **Configurazione in JSONB**: la preferenza si legge sempre intera ed è resiliente a evoluzioni future della struttura. I codici widget nel JSONB referenziano `ui.widget.codice` (stringa), mai l'`id`: protegge da cambi di ID cross-ambiente e permette di ignorare silenziosamente widget disattivati/rimossi.
* **Rilevamento preset aggiornato (DEF-2)**: `preset_base_id` + `preset_base_contenuto_aggiornato_il` + `preset_aggiornato_ignored_at` permettono di sapere se il preset di base è cambiato dopo l'ultimo salvataggio dell'utente, per il banner FE "preset aggiornato".

---

### Struttura JSONB `configurazione`

```json
{
  "widget": [
    {"codice": "resi_da_accreditare", "ordine": 1, "visibile": true},
    {"codice": "benvenuto", "ordine": 2, "visibile": true}
  ]
}
```

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | FK `django.auth_user` (aggiunta in `90_end`: auth_user creata da Django migrate) |
| `dashboard_id` | FK `ui.dashboard_definizione` |
| `preset_base_id` | FK `ui.dashboard_preset` (`ON DELETE SET NULL`): preset da cui è partita la personalizzazione |
| `preset_base_contenuto_aggiornato_il` | Snapshot di `dashboard_preset.contenuto_aggiornato_il` al salvataggio |
| `preset_aggiornato_ignored_at` | Tombstone: l'utente ha ignorato l'avviso "preset aggiornato" fino a qui |
| `configurazione` | JSONB, chiavi facoltative: widget (codice, ordine, visibile), dimensione_max; una chiave assente segue lo standard |

**UNIQUE** `(auth_user_id, dashboard_id)`: un solo record per utente/dashboard.

---

### Coerenza dei campi derivati

Il trigger [trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts](/dbzero/ui/funzioni/trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts) azzera `preset_base_contenuto_aggiornato_il` e `preset_aggiornato_ignored_at` quando `preset_base_id` cambia (`IS DISTINCT FROM`), impedendo un banner "preset aggiornato" basato su uno snapshot orfano.

---

### Note operative

* La FK verso `django.auth_user` è in `90_end` perché `auth_user` è creata da Django migrate, dopo Liquibase (pattern identico a `ui.lista_preferenza_utente`).
* Il frontend scrive qui al salvataggio della personalizzazione; la lettura passa **sempre** dalla funzione di risoluzione, mai da questa tabella direttamente.

---

### Note di migrazione

* 2026-11-08 — lo snapshot `preset_base_data_update` si rinomina `preset_base_contenuto_aggiornato_il` (`brief-db-revisione-dbops`, giro 7-bis blocco c). Le due FK verso dashboard e preset sono in eccezione al guard ATTIVO.
