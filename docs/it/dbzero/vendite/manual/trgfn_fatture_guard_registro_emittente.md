## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_fatture_guard_registro_emittente`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)
>
Approfondimenti funzioni:
>
[vendite.fn_lookup_registro_id](/dbzero/vendite/funzioni/fn_lookup_registro_id)
> • [vendite.fn_get_next_progressivo](/dbzero/vendite/manual/fn_get_next_progressivo)

---
### 🎯 Scopo Principale
(latest review 30-08-2026)

Impedisce che una fattura finisca su un **registro che non è del proprio
emittente**.

---

### Il difetto che chiude, ed era muto

Fino al 30 agosto 2026 niente legava il registro di una fattura all'emittente
della fattura. Sembra un problema piccolo, e invece è quello che non si vede.

⚠️ **Due emittenti sullo stesso registro non producono numeri doppi.** Il contatore
è uno solo: i numeri escono tutti diversi, il controllo di unicità non ha niente da
respingere, e nessun errore compare da nessuna parte.

⛔ Quello che si rompe è l'**attribuzione**: due partite IVA pescano dalla stessa
serie, e **nessuna delle due** ha una propria progressione. La numerazione, che è
il documento che le distingue davanti al fisco, diventa una sequenza condivisa.

⭐ È esattamente il motivo per cui serviva un controllo e non si poteva aspettare
un errore: non ce n'era nessuno da aspettare.

---

### Perché un controllo e non un vincolo di tabella

Un vincolo di tabella sarebbe stato verificato **su tutto il pregresso**, e sul
pregresso avrebbe fallito. Ripuntare una fattura già numerata non è una
correzione: le cambia il sezionale, cioè l'identità stessa del suo numero.

⭐ Il controllo presidia il **futuro** e lascia stare la storia. La storia
incoerente resta, ed è **dichiarata**, non ripulita.

---

### Guarda solo quando serve

Scatta quando si crea una fattura e quando si toccano **quelle due colonne**, non
a ogni modifica. Con un controllo generico, ogni passaggio di stato e ogni
ricalcolo di totali rivaliderebbe la coppia — e una fattura storica su un registro
non più coerente diventerebbe **impossibile da modificare**, con un errore che
parla di due colonne che nessuno stava toccando.

---

### Tace su cose che non sono sue

Se il registro indicato non esiste affatto, questo controllo **non dice niente** e
lascia parlare il vincolo di integrità. Un controllo che diagnostica anche i
problemi degli altri produce due messaggi per un difetto solo.

---

### Impatto e Vantaggi

* ogni emittente ha davvero la **propria** numerazione, e non solo sulla carta;
* insieme all'obbligo di indicare l'emittente su ogni registro, il caso «registro
  di nessuno» smette semplicemente di esistere.
