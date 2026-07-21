## 📘 Documentazione Concettuale – Tabella `ui.widget`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione)
> [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget)
> [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget)
>
> Funzione:
>
> [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config)

La tabella **`ui.widget`** è il **catalogo globale dei widget** delle dashboard. Ogni widget è una card KPI: un numero, una soglia di attenzione e un deep-link a una vista in stato preimpostato. È l'analogo di [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna), ma con una differenza portante: il widget è **globale**, non legato a una singola dashboard.

---

### 🎯 Scopo Principale

* **Catalogo globale**: un widget (es. `resi_da_accreditare`) ha senso in home oggi e potrebbe averlo in una dashboard di magazzino domani, senza duplicarne la definizione. Il legame widget↔dashboard vive nella tabella di composizione [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget). Il `codice` è perciò **unico globalmente**.
* **Zero logica di business**: i tre campi `deep_link`, `contatore_key`, `soglia` sono **opachi** al DB. Il DB li conserva e li restituisce; non li interpreta né li valuta. La grammatica route+stato è del frontend, il calcolo del contatore è del backend.
* **Gating permessi dichiarativo**: il widget dichiara `area_id` e/o `azione_id` (entrambi nullable) con la stessa semantica delle rotte di menu. La funzione di risoluzione filtra i widget non autorizzati; nessuna tabella permessi dedicata (a differenza di `ui.lista_colonna_permesso`), perché un widget o lo vedi o non lo vedi.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `codice` | Identificatore stabile **globale** del widget; referenziato nel JSONB della preferenza utente |
| `etichetta` / `etichetta_i18n_key` | Etichetta letterale e chiave i18n (vue-i18n) |
| `tipo_widget` | ENUM `ui.tipo_widget` (oggi solo `kpi`): forma del widget, per il componente FE |
| `deep_link` | JSONB opaco: route+stato preimpostato posseduti dal FE |
| `contatore_key` | Chiave del KPI da mostrare; il calcolo è responsabilità BE |
| `soglia` | JSONB opaco: come/quando allarmare (interpretato dal FE) |
| `area_id` | FK `config.aree_funzionali` (nullable). Visibile solo se `livello_area <> BLOCCATO`. NULL = non gated |
| `azione_id` | FK `config.azioni_processo` (nullable). Visibile solo se azione abilitata. NULL = non gated |
| `attivo` | Disattivazione logica: un widget disattivato sparisce da tutti gli utenti, preferenza inclusa |

---

### Relazioni

`ui.widget` è referenziata da:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `ui.dashboard_widget` | `widget_id` | Appartenenza del widget al pool di una dashboard |
| `ui.dashboard_preset_widget` | `widget_id` | Presenza del widget in un preset |

E referenzia:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `config.aree_funzionali` | `area_id` | Gating per area (nullable) |
| `config.azioni_processo` | `azione_id` | Gating per azione (nullable) |

---

### Note operative

* **Vincolo "mai vuota"** (seed): il catalogo deve includere almeno un widget **non-gated** (`area_id`/`azione_id` entrambi NULL, es. card di benvenuto). Altrimenti il filtro permessi può svuotare la home a un utente senza permessi. La struttura non lo garantisce: è responsabilità del seed.
* I codici widget nel JSONB della preferenza referenziano `ui.widget.codice`, mai l'`id`: protegge da cambi di ID cross-ambiente e permette di ignorare silenziosamente widget disattivati/rimossi.
* `deep_link`/`soglia`: definirne la grammatica lato FE prima di seedare i widget con stato preimpostato.
