## 📘 Documentazione Concettuale – Funzione `ui.fn_guard_misura_pagina`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo delle misure ammesse
>
> Approfondimento funzioni:
>
> * [ui.fn_misura_pagina_ammessa](/dbzero/ui/funzioni/fn_misura_pagina_ammessa) — la domanda a cui il guard si appoggia
> * [ui.trgfn_ui_lista_preset_guard_pagina_dimensione](/dbzero/ui/funzioni/trgfn_ui_lista_preset_guard_pagina_dimensione) — il guard sul preset
> * [ui.trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione](/dbzero/ui/funzioni/trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione) — il guard sulla preferenza

---

### 🎯 Scopo Principale

`ui.fn_guard_misura_pagina` rifiuta una misura «righe per pagina» che non è un numero intero del
catalogo, con un messaggio che riporta il valore scritto e le misure ammesse.

---

### Un rifiuto solo, per preset e preferenze

La chiamano i due guard di scrittura: quello del preset di una lista e quello della preferenza di
una persona. Riceve il valore com'è scritto, in JSONB, perché nella preferenza la misura sta in un
campo libero e può non essere un numero: così il rifiuto parte da un punto solo, con lo stesso
codice, per una misura fuori catalogo e per un valore che numero non è.

---

### Che cosa passa e che cosa no

* Nessun valore passa: vuol dire «il default».
* Un numero intero del catalogo passa.
* Si rifiuta una stringa, anche se contiene un numero, un numero con decimali, un numero negativo,
  un oggetto o un elenco, e un intero che non è nel catalogo.

Il controllo della forma viene prima della domanda al catalogo: un valore non intero non arriva mai
a un cast che solleverebbe un errore tecnico al posto del codice di catalogo.

---

### ⚠️ Che cosa oggi non copre

* **Giudica il valore anche quando non cambia.** Il guard della preferenza riceve la misura com'è
  nella riga nuova: una preferenza la cui misura è uscita dal catalogo dopo il salvataggio non si
  modifica più, in nessuna chiave, finché la misura non si toglie o si cambia nella stessa scrittura.
* **La forma della misura ha due sedi.** Il guard ammette solo un numero JSON; la lista
  configurabile, in lettura, legge anche una stringa di sole cifre come una misura. Un valore che il
  guard rifiuta alla scrittura, la lettura lo onora.
* **Con un catalogo vuoto** l'elenco delle misure ammesse nel messaggio è vuoto.

---

### Codici errore

* `E_UI_MISURA_PAGINA_NON_AMMESSA` — misura fuori catalogo, o valore che non è un numero intero.
  Il campo dell'errore è `pagina_dimensione`.

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — preset e preferenza con una misura fuori catalogo, la
  stringa che contiene un numero, il valore assente che passa, e il guard eseguibile
  dall'applicazione.

---

### Note di migrazione

* 2026-09-30 — nasce col catalogo delle misure: prima una misura fuori elenco passava, e il
  selettore della lista restava senza misura scelta.

---

{% include-markdown "signature-core.md" %}
