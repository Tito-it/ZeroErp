## 📘 Documentazione Concettuale – Funzione `ui.fn_get_misure_pagina()`

> 👀 **Vedi anche**
>
> **Il catalogo:** [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina)

---

### 🎯 Scopo Principale
(scritta il 30-09-2026)

Dà all'applicazione, in una lettura sola, **le misure «righe per pagina»** che
il paginatore deve offrire (in ordine crescente) e **i due default**: compatta
(drawer e dialog) e pagina.

---

### Regole

* La serve il backend a **tutti** i paginatori, anche quelli che non sono liste configurabili (tabelle, dialog, cruscotti).
* Se un default manca nel catalogo, solleva: non risponde mai un valore vuoto.

---

### Storia

* 2026-09-30 — nasce con il catalogo delle misure di pagina. Brief: brief-db-misure-pagina-catalogo.

{% include-markdown "signature-core.md" %}
