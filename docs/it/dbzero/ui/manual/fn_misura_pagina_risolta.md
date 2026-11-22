## 📘 Documentazione Concettuale – Funzione `ui.fn_misura_pagina_risolta`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo delle misure e dei default per uso
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — la misura del preset
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — l'uso della lista (`uso_misura`)
>
> Approfondimento funzioni:
>
> * [ui.fn_misura_pagina_ammessa](/dbzero/ui/funzioni/fn_misura_pagina_ammessa) — se una misura è nel catalogo
> * [ui.fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default) — il default di un uso
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la configurazione della lista, che la legge
> * [ui.fn_misura_lista](/dbzero/ui/funzioni/fn_misura_lista) — la sola misura di una lista, che la legge
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — le righe per pagina

---

### 🎯 Scopo Principale

`ui.fn_misura_pagina_risolta` decide quante righe per pagina mostra una lista, date le tre cose che
possono dirlo: la scelta dell'utente, il preset di base e l'uso della lista. È l'unico posto in cui la
regola è scritta: la leggono la configurazione della lista e la funzione che risponde la sola misura.

---

### La regola

1. Lo **standard** è la misura del preset di base, se è nel catalogo
   [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina). Altrimenti è il default del catalogo per
   l'uso della lista: `COMPATTA` per le liste mostrate in un drawer o in un dialog, `PAGINA` per le
   pagine.
2. Risponde la misura della **preferenza**, se è nel catalogo. Altrimenti risponde lo standard.

Una misura che esce dal catalogo smette di valere, che sia nella preferenza o nel preset: non è più una
scelta che il paginatore può mostrare. «Nessuna misura» (`NULL`) vale come una misura fuori catalogo.

---

### Che cosa esce

Una riga sola:

* **misura** — la misura che risponde;
* **standard** — quella che risponderebbe senza la preferenza (il drawer della lista la mostra come
  «come lo standard»);
* **origine** — da dove viene la misura: `preferenza`, `preset` o `catalogo`. La configurazione della
  lista rende `preset` con l'ambito del preset di base (ruolo, azienda, sistema).

La misura non è mai `NULL`.

---

### Codici errore

* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — il catalogo non ha il default dell'uso della lista. Si chiede
  quando il preset non dà una misura del catalogo, perché serve allo standard: in quel caso un catalogo
  senza default ferma la risposta **anche con una preferenza valida**. Con un preset nel catalogo il
  default non si chiede. Un catalogo senza il default di un uso non si salva (lo rifiuta il trigger
  differito di [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina)): l'errore dice un catalogo rotto.

---

### Test

* `db/pgtap/ui/test-ui-misura-lista-e-contesto-ricerca-v1.sql` — i quattro rami: la preferenza nel
  catalogo, la preferenza fuori catalogo, nessuna misura, il preset fuori catalogo.

---

### Note di migrazione

* 2026-11-22 — nasce, estratta dalla configurazione della lista quando la stessa regola è servita una
  seconda volta (la sola misura di una lista, per il backend).

---

{% include-markdown "signature-core.md" %}
