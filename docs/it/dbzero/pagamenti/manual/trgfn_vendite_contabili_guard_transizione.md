## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_guard_transizione`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — dove è montato
> * [pagamenti.transizioni_stati_contabile](/dbzero/pagamenti/tabelle/transizioni_stati_contabile) — la matrice che legge
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — da dove prende i codici per la frase
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — le condizioni sulle transizioni che la matrice non porta
> * [pagamenti.trgfn_vendite_contabili_righe_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_transizione) — il gemello sulle righe
> * [vendite.trgfn_commesse_guard_transizione](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione) — lo stesso schema, sulle commesse

---

### 🎯 Scopo Principale

Fa rispettare il grafo degli stati della distinta contabile: un cambio di stato è
ammesso solo se la coppia (stato di partenza, stato d'arrivo) è presente e **attiva** in
[pagamenti.transizioni_stati_contabile](/dbzero/pagamenti/tabelle/transizioni_stati_contabile).

⛔ **Nessun grafo scritto nel codice**: la regola sta in una tabella, così si legge e si
cambia senza toccare la funzione. È lo stesso schema dei guard di transizione degli altri
domini.

---

### Scatta solo quando lo stato cambia davvero

Un aggiornamento che nomina la colonna di stato senza cambiarne il valore non è una
transizione e passa senza controlli.

⚠️ **Mai sulla nascita**, ed è una regola del progetto: una distinta deve poter **nascere**
in uno stato qualunque. Non è teorico: il giro dei fondi fattura crea le sue distinte
direttamente in `VALIDATA`, perché lì non c'è digitazione e nascono già finite.

---

### La frase nomina gli stati per codice interno

Il messaggio dice i **codici di stato**, non gli id, e usa `codice_interno`, che è
immutabile, non `codice`, che l'utente può rinominare.

Il codice errore è **distinto** da quello della riga: le due macchine hanno stati diversi, e
con un codice solo il messaggio manderebbe a guardare il documento sbagliato.

---

### Codici errore

* `E_CONTABILE_TRANSIZIONE_NON_AMMESSA` — la coppia di stati non è in matrice, o è spenta; la
  frase nomina la distinta e i due stati.

---

### Test

`db/pgtap/pagamenti/test-transizioni-stati-contabili.sql` — una transizione ammessa passa,
una non ammessa è rifiutata, da uno stato finale non si esce, la nascita non è vincolata
dalla matrice.

---

### Note di migrazione

* 2026-08-21 — nasce insieme alla matrice: fino ad allora `pagamenti` era l'unico dominio con
  degli stati e nessuna regola su come ci si passa.

---

{% include-markdown "signature-core.md" %}
