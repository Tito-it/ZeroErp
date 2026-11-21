## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la tabella su cui il guard è montato
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo delle misure ammesse
>
> Approfondimento funzioni:
>
> * [ui.fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina) — il rifiuto a cui il guard delega
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la lettura della preferenza
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — le preferenze di una persona

---

### 🎯 Scopo Principale

`ui.trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione` fa sì che la misura «righe per
pagina» salvata nella preferenza di una persona sia una misura del catalogo, o nessuna.

---

### Dove una FK non arriva

Nella preferenza la misura sta nella configurazione JSONB, alla chiave `pagina_dimensione`: una FK
non la raggiunge. Il guard scatta alla nascita della preferenza e a ogni modifica della
configurazione, e passa il valore com'è scritto a
[fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina): una misura fuori catalogo e
un valore che non è un numero intero si rifiutano con lo stesso codice.

La chiave assente, o vuota, passa: la lista segue allora lo standard (la misura del preset di base,
o il default del catalogo).

---

### ⚠️ Che cosa oggi non copre

* **Una misura uscita dal catalogo blocca la preferenza.** Il catalogo non sa delle preferenze: una
  misura citata solo da preferenze si toglie, o si riscrive, senza rifiuto. Da quel momento il guard
  rifiuta ogni modifica della configurazione che conservi la chiave, anche se cambia soltanto le
  colonne, l'ordinamento o i filtri. La lettura, invece, scarta la misura e risponde lo standard. Oggi
  il caso lo evita il client, che risalva la misura solo quando la lettura la dice scelta dalla
  persona.
* **La lettura è più larga della scrittura.** La lista configurabile, quando legge la preferenza,
  accetta anche una stringa di sole cifre come misura; il guard la rifiuta. Una riga scritta prima del
  guard, o senza passare dal trigger, viene onorata.

---

### Codici errore

* `E_UI_MISURA_PAGINA_NON_AMMESSA` — la misura della preferenza non è nel catalogo, o non è un
  numero intero.

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — preferenza con una misura fuori catalogo, con una
  stringa che contiene un numero, senza misura, e il trigger presente.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — la preferenza di sola misura
  e la preferenza senza misura nella lettura.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure: prima una preferenza poteva salvare qualunque
  numero, anche uno che il selettore non offre.

---

{% include-markdown "signature-core.md" %}
