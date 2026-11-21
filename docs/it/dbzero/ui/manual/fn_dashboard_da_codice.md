## 📘 Documentazione Concettuale – Funzione `ui.fn_dashboard_da_codice`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione) — il catalogo delle dashboard
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — legge da qui la dashboard che risolve
> * [ui.fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice) — il gemello delle liste

---

### 🎯 Scopo Principale

La funzione restituisce la riga di una dashboard configurabile dato il suo codice, se la dashboard esiste
ed è accesa; altrimenti rifiuta con `E_UI_DASHBOARD_NON_TROVATA`. È la sede unica della regola
«dashboard assente o spenta»: la risoluzione della dashboard e il backend passano da qui.

---

### Assente e spenta sono la stessa risposta

Una dashboard che non esiste e una dashboard spenta danno lo stesso rifiuto, col codice nella frase: per
chi apre la home le due cose non si distinguono, e una dashboard spenta non risponde con i suoi preset.
Chi vuole «nessuna dashboard» invece del rifiuto intercetta il codice.

---

### Restituisce la riga intera

Il risultato ha la forma della tabella: chi la chiama prende i campi che gli servono, di solito l'`id`.

---

### ⚠️ Che cosa oggi non copre

* **Il codice si confronta così com'è**: maiuscole, minuscole e spazi contano, e un codice `NULL` dà il
  rifiuto con un codice vuoto nella frase.

---

### Codici errore

* `E_UI_DASHBOARD_NON_TROVATA` — nessuna dashboard accesa con quel codice.

---

### Test

* `db/pgtap/ui/test-ui-catalogo-dashboard-v1.sql` — la riga della dashboard accesa; il codice assente, il
  codice `NULL` e la dashboard spenta rifiutati, anche dalla risoluzione.

---

### Note di migrazione

* 2026-11-21 — nasce, e prende il posto della lettura per codice scritta dentro la risoluzione.

---

{% include-markdown "signature-core.md" %}
