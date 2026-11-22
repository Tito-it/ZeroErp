## 📘 Documentazione Concettuale – Funzione `ui.fn_misura_lista`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la misura scelta dall'utente
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — la misura del preset
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo delle misure
>
> Approfondimento funzioni:
>
> * [ui.fn_misura_pagina_risolta](/dbzero/ui/funzioni/fn_misura_pagina_risolta) — la regola della misura
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — la scelta del preset di base
> * [ui.fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice) — la riga della lista dal codice
> * [ui.fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista) — la gemella, per l'ordinamento
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la configurazione intera
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — le righe per pagina

---

### 🎯 Scopo Principale

`ui.fn_misura_lista` risponde quante righe per pagina mostra una lista a un utente: lo stesso numero che
la configurazione della lista dà in `pagina_dimensione`, senza risolvere colonne e permessi.

---

### Da dove viene

Dalla regola di [fn_misura_pagina_risolta](/dbzero/ui/funzioni/fn_misura_pagina_risolta), con i tre
ingressi letti qui:

* la misura della **preferenza** dell'utente sulla lista, se ne ha una;
* quella del **preset di base**, scelto da [fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base)
  come per la configurazione della lista (il preset di ruolo solo con la veste, poi quello dell'azienda,
  poi quello di sistema);
* l'**uso** della lista (`COMPATTA` o `PAGINA`), che dà il default del catalogo quando nessuno dei due
  dice una misura valida.

Il numero non è mai `NULL`.

---

### ⭐ A che cosa serve

Il backend serve una lista configurabile anche a un chiamante che non dice quante righe vuole. Invece di
una costante sua, chiede la misura al database con questa funzione: una chiamata leggera, gemella di
[fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista), fatta dallo stesso punto del backend.
La regola resta una: quella che la configurazione della lista mostra all'utente.

---

### Codici errore

* `E_UI_LISTA_NON_TROVATA` — lista inesistente o spenta (dal building block della lista).
* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — il catalogo non ha il default dell'uso della lista.

---

### Test

* `db/pgtap/ui/test-ui-misura-lista-e-contesto-ricerca-v1.sql` — la misura del preset, il default
  `COMPATTA` e la misura della preferenza, ognuna uguale a quella della configurazione della lista; la
  lista inesistente.

---

### Note di migrazione

* 2026-11-22 — nasce, chiesta dal backend per le liste configurabili chiamate senza un numero di righe.

---

{% include-markdown "signature-core.md" %}
