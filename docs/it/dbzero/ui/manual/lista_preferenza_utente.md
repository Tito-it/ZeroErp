## 📘 Documentazione Concettuale – Tabella `ui.lista_preferenza_utente`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
> [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione)
> [ui.lista_preset](/dbzero/ui/tabelle/lista_preset)
>
> Funzione:
>
> [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)

La tabella **`ui.lista_preferenza_utente`** memorizza la **preferenza personale dell'utente** per una lista. Un solo record per coppia `(auth_user, lista)`. La preferenza vale **chiave per chiave**: ciò che l'utente ha scelto prevale sui preset, ciò che non ha scelto segue lo standard.

---

### 🎯 Scopo Principale

* **Personalizzazione individuale**: l'operatore può scegliere quali colonne vedere, in che ordine, con quale larghezza, ordinamento, filtri preimpostati e righe per pagina. Ogni chiave scelta è il livello massimo della cascata **per quella chiave** e prevale su qualsiasi preset.
* ⭐ **Chiave assente = «come lo standard»** (dal 1-11-2026): la preferenza porta solo le chiavi che l'utente ha scelto. Una chiave assente (o `null`) la risolve [`fn_resolve_lista_config`](/dbzero/ui/funzioni/fn_resolve_lista_config) dal preset di base, o dal catalogo; quindi un cambio del preset arriva anche a chi ha personalizzato altro. Chi salva rimanda solo le chiavi che il resolver dice di `origine` `preferenza`, più quella toccata: rimandare la configurazione risolta per intero trasformerebbe in «scelta» una copia del preset, e la congelerebbe. Una preferenza che resta senza chiavi si **cancella**: vuota direbbe «tutto come lo standard», cioè nessuna preferenza, ma lo snapshot del preset di base accenderebbe il banner del preset aggiornato senza niente da riconciliare.
* **JSONB per resilienza**: la configurazione è in un unico campo JSONB invece di righe separate per colonna. Questo permette di leggere la preferenza sempre completa in una sola query e di aggiungere futuri attributi (es. vista compatta, raggruppamenti) senza alterare lo schema.
* **Rilevamento preset obsoleto**: `preset_base_data_update` è uno snapshot di `lista_preset.data_update` al momento del salvataggio. Se `lista_preset.data_update > preset_base_data_update`, il preset su cui si basava la preferenza è stato aggiornato — il frontend può avvisare l'utente con un banner "Configurazione aggiornata disponibile".

---

### Struttura JSONB `configurazione`

Le chiavi sono quattro, tutte facoltative. Esempio di una preferenza che sceglie colonne e righe per pagina, e lascia ordinamento e filtri al preset:

```json
{
  "colonne": [
    {"codice": "ragione_sociale", "ordine": 1, "larghezza": 240, "visibile": true, "fissata": true},
    {"codice": "partita_iva",     "ordine": 2, "larghezza": 140, "visibile": true, "fissata": false},
    {"codice": "stato",           "ordine": 3, "larghezza": 100, "visibile": false,"fissata": false}
  ],
  "pagina_dimensione": 50
}
```

> I codici colonna referenziano `lista_colonna.codice` (stringa), non l'`id` numerico. Questo protegge da cambi di ID e permette di ignorare silenziosamente colonne disattivate nel catalogo.

> `pagina_dimensione` (dal 30-09-2026) deve essere una misura del catalogo [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina), o mancare (vale lo standard: la misura del preset di base, o il default del catalogo). Una misura fuori catalogo — o un valore che non è un numero intero — viene rifiutata al salvataggio (`trg_ui_lista_preferenza_utente_a10_guard_pagina_ins_upd`). Una preferenza salvata prima con una misura non più ammessa non rompe niente: la lista risponde lo standard.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | Utente proprietario (FK a `django.auth_user` aggiunta in `90_end`) |
| `preset_base_id` | Preset da cui è partita la personalizzazione (riferimento storico, può diventare NULL) |
| `preset_base_data_update` | Snapshot per rilevare se il preset padre è stato modificato dopo il salvataggio |
| `configurazione` | Le scelte dell'utente in JSONB, chiave per chiave (colonne, ordinamento, filtri, paginazione); una chiave assente segue lo standard |

---

### Note operative

* La FK verso `django.auth_user` è aggiunta in `90_end` perché `auth_user` è creata da Django migrate, che gira dopo Liquibase. Pattern identico a `config.parameter_overrides`.
* Nessun `user_insert`/`user_update`: l'identità dell'utente è già in `auth_user_id` e la preferenza è sempre di proprietà esclusiva dell'utente stesso.
* On DELETE CASCADE su `auth_user_id`: eliminare l'utente rimuove automaticamente le sue preferenze.
