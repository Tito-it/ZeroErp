## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_misure_pagina_guard_default_per_uso`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo che sorveglia
>
> Approfondimento funzioni:
>
> * [ui.fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default) — la domanda che fa per ogni uso
> * [ui.fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina) — la lettura che un catalogo senza default romperebbe

---

### 🎯 Scopo Principale

`ui.trgfn_misure_pagina_guard_default_per_uso` tiene il catalogo delle misure «righe per pagina»
sempre con un default per ogni uso (`COMPATTA` e `PAGINA`, i valori dell'enum `ui.uso_misura_pagina`).
Senza, ogni lettura delle misure si fermerebbe, e con lei ogni paginatore dell'applicazione.

---

### A fine transazione, non a ogni riga

L'indice unico del catalogo dice già che un uso sta su **al più** una riga. Per spostare un default
da una misura a un'altra, quindi, c'è per forza un momento senza: prima si toglie l'uso da una riga,
poi lo si dà all'altra. Per questo la funzione è montata come **constraint trigger differito**
(`DEFERRABLE INITIALLY DEFERRED`), riga per riga, `AFTER INSERT OR UPDATE OF uso_default OR DELETE`:
giudica al commit, quando il catalogo è nella sua forma finale.

A ogni scatto chiede il default di ogni uso a
[fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default), che solleva se manca. La
regola «un default per uso» resta così in una sede sola, e l'elenco degli usi viene dall'enum, non da
una lista scritta qui.

Con `SET CONSTRAINTS ALL IMMEDIATE`, come nei pgTAP, scatta a fine istruzione: lì lo spostamento si
prova rimettendo in differito questo solo trigger.

---

### Codici errore

* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — a fine transazione un uso è rimasto senza default.
* `E_TRIGGER_ARGOMENTI_INVALIDI` — la funzione montata su un'altra tabella, o non come trigger
  `AFTER` di riga.

---

### Test

* `db/pgtap/ui/test-ui-misure-catalogo-e-uso-v1.sql` — togliere il default `PAGINA` senza spostarlo è
  rifiutato; spostarlo nella stessa transazione passa, e la lista risponde il default nuovo.

---

### Note di migrazione

* 2026-11-21 — nasce: togliere un default riusciva, e il catalogo rotto lo scopriva il primo utente
  che apriva una pagina.

---

{% include-markdown "signature-core.md" %}
