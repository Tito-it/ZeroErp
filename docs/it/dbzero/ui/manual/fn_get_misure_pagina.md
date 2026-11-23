## 📘 Documentazione Concettuale – Funzione `ui.fn_get_misure_pagina`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo che la funzione legge
>
> Approfondimento funzioni:
>
> * [ui.fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default) — il default di un uso, mai vuoto
> * [ui.trgfn_misure_pagina_guard_default_per_uso](/dbzero/ui/funzioni/trgfn_misure_pagina_guard_default_per_uso) — il catalogo ha un default per ogni uso

---

### 🎯 Scopo Principale

`ui.fn_get_misure_pagina` dà all'applicazione, in una lettura sola, le misure «righe per pagina» del
catalogo in ordine crescente e il default di ogni uso: quello compatto (drawer e dialog) e quello della
pagina intera.

---

### Una lettura per tutti i paginatori

Il backend la espone con un endpoint, e il frontend la legge una volta, prima di aprire qualunque
pagina: tutti i paginatori, anche quelli che non sono liste configurabili, prendono da qui le
opzioni del selettore e la misura con cui partono.

---

### Che cosa risponde

* **misure** — le misure del catalogo, in ordine crescente;
* **default_per_uso** — un oggetto con una chiave per ogni uso (`COMPATTA`, `PAGINA`) e il suo default.
  Gli usi vengono dall'elenco degli usi del database, non sono scritti nella funzione: un uso nuovo
  compare qui senza toccarla.

---

### Mai un default vuoto

I default vengono da [fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default): se il
catalogo non ne dichiara uno, la lettura intera solleva invece di rispondere un default vuoto. Il catalogo
non si salva senza un default per ogni uso (lo rifiuta
[il trigger differito del catalogo](/dbzero/ui/funzioni/trgfn_misure_pagina_guard_default_per_uso)):
l'errore dice un catalogo rotto, non un caso da gestire.

---

### Codici errore

* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — manca il default di un uso (sollevato da
  `fn_misura_pagina_default`).

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — le misure in ordine, le stesse del catalogo, e i default
  uguali a quelli del building block; `default_per_uso` con una chiave per ogni uso, una risposta senza
  altre chiavi, e il corpo che legge l'elenco degli usi.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure: prende il posto delle costanti di paginazione del
  frontend.
* 2026-11-22 — i default per uso dall'elenco degli usi (`default_per_uso`); le due chiavi di prima
  restano finché il backend non passa.
* 2026-11-23 — escono `default_compatta` e `default_pagina`: il frontend legge `default_per_uso`.

---

{% include-markdown "signature-core.md" %}
