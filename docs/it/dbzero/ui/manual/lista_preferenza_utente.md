## 📘 Documentazione Concettuale – Tabella `ui.lista_preferenza_utente`

> 👀 **Vedi anche**
>
> [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione)
> [ui.lista_preset](/dbzero/ui/tabelle/lista_preset)
>
> Funzione:
>
> [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)

La tabella **`ui.lista_preferenza_utente`** memorizza la **preferenza personale dell'utente** per una lista. Un solo record per coppia `(auth_user, lista)`: le personalizzazioni dell'utente sovrascrivono la cascata dei preset.

---

### 🎯 Scopo Principale

* **Personalizzazione individuale**: l'operatore può scegliere quali colonne vedere, in che ordine, con quale larghezza, ordinamento e filtri preimpostati. Questa preferenza è il livello massimo della cascata e sovrascrive qualsiasi preset.
* **JSONB per resilienza**: la configurazione è in un unico campo JSONB invece di righe separate per colonna. Questo permette di leggere la preferenza sempre completa in una sola query e di aggiungere futuri attributi (es. vista compatta, raggruppamenti) senza alterare lo schema.
* **Rilevamento preset obsoleto**: `preset_base_data_update` è uno snapshot di `lista_preset.data_update` al momento del salvataggio. Se `lista_preset.data_update > preset_base_data_update`, il preset su cui si basava la preferenza è stato aggiornato — il frontend può avvisare l'utente con un banner "Configurazione aggiornata disponibile".

---

### Struttura JSONB `configurazione`

```json
{
  "colonne": [
    {"codice": "ragione_sociale", "ordine": 1, "larghezza": 240, "visibile": true, "fissata": true},
    {"codice": "partita_iva",     "ordine": 2, "larghezza": 140, "visibile": true, "fissata": false},
    {"codice": "stato",           "ordine": 3, "larghezza": 100, "visibile": false,"fissata": false}
  ],
  "ordinamento": [{"col": "ragione_sociale", "dir": "asc"}],
  "filtri": {"attivo": true},
  "pagina_dimensione": 50
}
```

> I codici colonna referenziano `lista_colonna.codice` (stringa), non l'`id` numerico. Questo protegge da cambi di ID e permette di ignorare silenziosamente colonne disattivate nel catalogo.

> `pagina_dimensione` (dal 30-09-2026) deve essere una misura del catalogo [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina), o mancare (vale il default). Una misura fuori catalogo — o un valore che non è un numero intero — viene rifiutata al salvataggio (`trg_ui_lista_preferenza_utente_a10_guard_pagina_ins_upd`). Una preferenza salvata prima con una misura non più ammessa non rompe niente: la lista risponde il default.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | Utente proprietario (FK a `django.auth_user` aggiunta in `90_end`) |
| `preset_base_id` | Preset da cui è partita la personalizzazione (riferimento storico, può diventare NULL) |
| `preset_base_data_update` | Snapshot per rilevare se il preset padre è stato modificato dopo il salvataggio |
| `configurazione` | Tutto il layout utente in JSONB (colonne, ordinamento, filtri, paginazione) |

---

### Note operative

* La FK verso `django.auth_user` è aggiunta in `90_end` perché `auth_user` è creata da Django migrate, che gira dopo Liquibase. Pattern identico a `config.parameter_overrides`.
* Nessun `user_insert`/`user_update`: l'identità dell'utente è già in `auth_user_id` e la preferenza è sempre di proprietà esclusiva dell'utente stesso.
* On DELETE CASCADE su `auth_user_id`: eliminare l'utente rimuove automaticamente le sue preferenze.
