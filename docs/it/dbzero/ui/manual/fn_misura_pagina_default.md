## 📘 Documentazione Concettuale – Funzione `ui.fn_misura_pagina_default`

> **Ultimo aggiornamento**: 21 novembre 2026
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
(drawer e dialog) o `PAGINA` (liste a pagina intera), i valori dell'enum `ui.uso_misura_pagina`.
L'uso arriva come testo: uno fuori vocabolario non è un errore di conversione, è il caso «nessun
default» qui sotto.

---

### Mai vuota

Se il catalogo non dichiara il default di quell'uso, o l'uso non è uno dei due, la funzione solleva:
è un catalogo rotto, non un dato dell'operatore. Un default vuoto arriverebbe al paginatore come un
selettore senza misura scelta.

---

### Chi la chiede

* [fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina), per i due default che manda
  all'applicazione;
* [fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config), per il ripiego sul default
  dell'uso della lista (`COMPATTA` o `PAGINA`) quando né la preferenza né il preset di base hanno una
  misura del catalogo;
* [trgfn_misure_pagina_guard_default_per_uso](/dbzero/ui/funzioni/trgfn_misure_pagina_guard_default_per_uso),
  che a fine transazione la chiede per ogni uso: il catalogo non resta senza un default.

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
* `db/pgtap/ui/test-ui-misure-catalogo-e-uso-v1.sql` — il ripiego `COMPATTA` di una lista compatta, e il
  default tolto senza spostarlo che il trigger differito rifiuta.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure: prende il posto del numero di default ripetuto nella
  funzione che risolve le liste.
* 2026-11-21 — l'uso diventa l'enum `ui.uso_misura_pagina`; la chiedono anche il ripiego per uso della
  lista e il trigger differito del catalogo.

---

{% include-markdown "signature-core.md" %}
