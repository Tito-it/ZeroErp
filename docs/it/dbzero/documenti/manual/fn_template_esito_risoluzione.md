## 📘 Documentazione Concettuale – Funzione `documenti.fn_template_esito_risoluzione`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — i modelli fra cui si sceglie, e il predefinito
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — i soli modelli che contano
> * [documenti.vw_template_risoluzione_emittente](/dbzero/documenti/views/vw_template_risoluzione_emittente) — la applica a ogni azienda, per la lista Modelli documento
>
> Approfondimento funzioni:
>
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la applica alla stampa, e ne fa errori
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §3.2, i due livelli

---

### 🎯 Scopo Principale

La regola dei due livelli, scritta una volta: per un'azienda e un documento (tipo e sorgente) dice con
che cosa si stampa, considerando solo i modelli che possono stampare. Restituisce sempre una riga: un
esito, il modello e la versione quando ci sono, e quanti modelli suoi l'azienda ha che possono
stampare.

---

### Gli esiti

| Esito | Quando | Modello e versione |
| --- | --- | --- |
| `EMITTENTE` | l'azienda ha modelli suoi che possono stampare, e il suo predefinito è fra questi | il suo predefinito |
| `SENZA_PREDEFINITO` | ha modelli suoi che possono stampare, ma il predefinito non c'è o non stampa | nessuno: lo standard non entra |
| `STANDARD` | non ne ha nessuno che stampi, e il predefinito standard può stampare | lo standard |
| `NON_RISOLTO` | non ne ha nessuno che stampi, e nemmeno il predefinito standard può stampare | nessuno |

Il predefinito è al più uno per azienda, tipo e sorgente fra i modelli attivi, e uno solo fra gli
standard: l'esito non dipende dall'ordine delle righe.

---

### ⭐ Una regola, due lettori

* `fn_risolvi_template_applicabile` la usa alla stampa, e sugli esiti negativi solleva il codice del
  caso;
* `vw_template_risoluzione_emittente` la applica a ogni azienda, per la lista Modelli documento.

Stampa e lista rispondono così allo stesso modo. La funzione non legge le aziende: chi la chiama ha
già l'azienda, e quale modello stampa non dipende da che cosa la sicurezza di riga lascia vedere.

---

### Test

* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — gli esiti, attraverso la porta della
  stampa.
* `db/pgtap/documenti/test-documenti-template-porta-unica-v1.sql` — la parità fra la vista e la stampa
  per `EMITTENTE`, `STANDARD` e `SENZA_PREDEFINITO`.

---

### Note di migrazione

* 2026-10-21 — nasce, per dare alla lista Modelli documento la stessa regola della stampa invece di
  una sua copia.

---

{% include-markdown "signature-core.md" %}
