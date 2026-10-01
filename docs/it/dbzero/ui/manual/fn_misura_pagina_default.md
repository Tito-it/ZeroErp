## 📘 Documentazione Concettuale – Funzione `ui.fn_misura_pagina_default()`

> 👀 **Vedi anche**
>
> **Il catalogo:** [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina)

---

### 🎯 Scopo Principale
(scritta il 30-09-2026)

La misura di default per un uso: `COMPATTA` (drawer e dialog) o `PAGINA` (pagine,
e il ripiego della lista quando nessuno ha scelto).

---

### Regole

* **Mai vuota**: se il catalogo non dichiara quel default, è un catalogo rotto e la funzione solleva `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE`. Un valore vuoto tornerebbe a video come il selettore vuoto da cui il cantiere è partito.
* La usano [fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) e [fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina).

---

### Storia

* 2026-09-30 — nasce con il catalogo delle misure di pagina. Brief: brief-db-misure-pagina-catalogo.

{% include-markdown "signature-core.md" %}
