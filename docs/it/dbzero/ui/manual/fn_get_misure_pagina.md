## 📘 Documentazione Concettuale – Funzione `ui.fn_get_misure_pagina`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo che la funzione legge
>
> Approfondimento funzioni:
>
> * [ui.fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default) — i due default, mai vuoti

---

### 🎯 Scopo Principale

`ui.fn_get_misure_pagina` dà all'applicazione, in una lettura sola, le misure «righe per pagina» del
catalogo in ordine crescente e i due default: quello compatto (drawer e dialog) e quello della
pagina intera.

---

### Una lettura per tutti i paginatori

Il backend la espone con un endpoint, e il frontend la legge una volta, prima di aprire qualunque
pagina: tutti i paginatori, anche quelli che non sono liste configurabili, prendono da qui le
opzioni del selettore e la misura con cui partono.

---

### Mai un default vuoto

I due default vengono da [fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default):
se il catalogo non ne dichiara uno, la lettura intera solleva invece di rispondere un default vuoto.
Un catalogo senza misure risponde un elenco vuoto, ma senza misure non c'è nemmeno un default, e la
lettura solleva comunque.

---

### ⚠️ Che cosa oggi non copre

* La funzione presuppone un catalogo con entrambi i default, ma il catalogo non lo garantisce: il
  vincolo ne ammette al più uno per uso, non esattamente uno. Una scrittura che toglie un default fa
  sollevare questa lettura, e con lei si ferma l'avvio di ogni pagina dell'applicazione.

---

### Codici errore

* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — manca il default compatto o quello della pagina intera
  (sollevato da `fn_misura_pagina_default`).

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — le misure in ordine, e i due default fra le misure
  offerte.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure: prende il posto delle costanti di paginazione del
  frontend.

---

{% include-markdown "signature-core.md" %}
