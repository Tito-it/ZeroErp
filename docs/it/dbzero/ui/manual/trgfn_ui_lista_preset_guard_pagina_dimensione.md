## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_preset_guard_pagina_dimensione`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — la tabella su cui il guard è montato
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo delle misure ammesse
>
> Approfondimento funzioni:
>
> * [ui.fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina) — il rifiuto a cui il guard delega
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — i preset delle liste

---

### 🎯 Scopo Principale

`ui.trgfn_ui_lista_preset_guard_pagina_dimensione` fa sì che la misura «righe per pagina» di un
preset di lista sia una misura del catalogo, o nessuna.

---

### Il codice di catalogo prima della FK

Il preset cita la misura con una FK verso il catalogo. Il guard scatta prima, alla nascita del preset
e quando cambia la sua misura, e passa il valore a
[fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina): una misura fuori catalogo
arriva come `E_UI_MISURA_PAGINA_NON_AMMESSA`, con l'elenco delle misure ammesse, invece che come
violazione grezza della FK. La FK resta come rete.

Il preset che non nomina la misura nasce senza: la colonna non ha un default, e la lista prende
allora il default `PAGINA` del catalogo.

---

### ⚠️ Che cosa oggi non copre

* Il guard non vede che cosa succede al catalogo dopo: una misura citata da un preset non si toglie,
  ma per la FK, col suo errore grezzo.

---

### Codici errore

* `E_UI_MISURA_PAGINA_NON_AMMESSA` — la misura del preset non è nel catalogo.

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — preset con una misura fuori catalogo alla nascita e alla
  modifica, con una misura del catalogo, senza misura, e il trigger presente.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure. Il trigger si monta dopo il seed dei preset.

---

{% include-markdown "signature-core.md" %}
