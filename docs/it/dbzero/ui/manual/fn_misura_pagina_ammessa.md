## 📘 Documentazione Concettuale – Funzione `ui.fn_misura_pagina_ammessa`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo che la funzione interroga
>
> Approfondimento funzioni:
>
> * [ui.fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina) — la usa per rifiutare una scrittura
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la usa per non rispondere una misura fuori catalogo

---

### 🎯 Scopo Principale

`ui.fn_misura_pagina_ammessa` risponde sì o no alla domanda «questa misura “righe per pagina” è nel
catalogo?».

---

### Una domanda, due lettori

È la sola sede della domanda. La fanno:

* il rifiuto delle scritture di preset e preferenze
  ([fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina));
* la lista configurabile quando si apre
  ([fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)), che scarta la misura della
  preferenza e quella del preset quando non sono più nel catalogo, e ripiega sul livello dopo.

Nessuna misura vuol dire «no»: una misura assente non è nel catalogo.

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — la domanda attraverso i suoi due lettori: il rifiuto di
  una misura fuori catalogo e la misura scelta che il resolver risponde.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure.

---

{% include-markdown "signature-core.md" %}
