## 📘 Documentazione Concettuale – Funzione `ui.fn_guard_misura_pagina()`

> 👀 **Vedi anche**
>
> **Il catalogo:** [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina)
>
> **La domanda:** [fn_misura_pagina_ammessa](/dbzero/ui/funzioni/fn_misura_pagina_ammessa)

---

### 🎯 Scopo Principale
(scritta il 30-09-2026)

**Rifiuta una misura «righe per pagina» che non è nel catalogo**, con un
messaggio che elenca quelle ammesse (`E_UI_MISURA_PAGINA_NON_AMMESSA`).

---

### Regole

* La chiamano i controlli sui **preset** delle liste e sulle **preferenze** salvate dalle persone.
* Nessuna misura (vuoto) passa: vuol dire «il default».
* Rifiuta anche un valore che non è un numero intero: nelle preferenze la misura sta in un campo libero.

---

### Storia

* 2026-09-30 — nasce con il catalogo delle misure di pagina. Brief: brief-db-misure-pagina-catalogo.

{% include-markdown "signature-core.md" %}
