## 📘 Documentazione Concettuale – Funzione `ui.fn_misura_pagina_default`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo che dichiara i default
>
> Approfondimento funzioni:
>
> * [ui.fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina) — la lettura unica per l'applicazione
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — il ripiego della lista configurabile

---

### 🎯 Scopo Principale

`ui.fn_misura_pagina_default` dà la misura «righe per pagina» di default per un uso: `COMPATTA`
(drawer e dialog) o `PAGINA` (liste a pagina intera).

---

### Mai vuota

Se il catalogo non dichiara il default di quell'uso, o l'uso non è uno dei due, la funzione solleva:
è un catalogo rotto, non un dato dell'operatore. Un default vuoto arriverebbe al paginatore come un
selettore senza misura scelta.

---

### Chi la chiede

* [fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina), per i due default che manda
  all'applicazione;
* [fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config), per il ripiego `PAGINA`
  quando né la preferenza né il preset di base hanno una misura del catalogo. La lista configurabile
  non chiede mai il default `COMPATTA`.

---

### Codici errore

* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — il catalogo non ha il default dell'uso chiesto, o l'uso è
  fuori vocabolario.

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — un default per uso, e l'uso fuori vocabolario che
  solleva invece di rispondere vuoto.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — il ripiego sul default
  `PAGINA` quando il preset non ha una misura.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure: prende il posto del numero di default ripetuto nella
  funzione che risolve le liste.

---

{% include-markdown "signature-core.md" %}
