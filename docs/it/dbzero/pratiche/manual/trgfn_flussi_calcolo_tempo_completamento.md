## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_calcolo_tempo_completamento`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella su cui è montata
> * [pratiche.formule_tempo](/dbzero/pratiche/tabelle/formule_tempo) — le formule da/a e i giorni previsti
> * [pratiche.calcoli_tempo](/dbzero/pratiche/tabelle/calcoli_tempo) — dove nasce e si chiude il conteggio
>
> Approfondimento funzioni:
>
> * [pratiche.fn_calcola_tempo_netto_da_a](/dbzero/pratiche/funzioni/fn_calcola_tempo_netto_da_a) — i giorni netti, al netto delle sospensioni

---

### 🎯 Scopo Principale

`pratiche.trgfn_flussi_calcolo_tempo_completamento` gestisce il ciclo di vita dei calcoli di tempo del
modello da/a: quando un flusso va `COMPLETATO`, apre i conteggi che partono da lui e chiude quelli che
arrivano a lui.

Lo stesso flusso può essere la partenza di una formula e l'arrivo di un'altra.

---

### Quando scatta

È montata `AFTER UPDATE OF stato_id`, riga per riga, nella fase `_z90_`, e scatta quando lo stato cambia.
La funzione agisce solo se il nuovo stato è `COMPLETATO` e il flusso è nato da un template.

---

### Il flusso completato come partenza: si apre il conteggio

Per ogni formula attiva del tipo di prestazione della pratica che parte dal template del flusso:

* si cerca nella stessa pratica il flusso d'arrivo, per template;
* se c'è, e il conteggio per quella combinazione (pratica, partenza, arrivo, formula) non esiste ancora,
  nasce una riga di calcolo che parte dalla fine del flusso completato e fotografa i giorni previsti
  dalla formula;
* ⭐ **ordine invertito**: se il flusso d'arrivo è già completato, la riga si chiude subito.

⚠️ Il conteggio nasce solo se il flusso d'arrivo esiste già nella pratica quando la partenza si completa.

---

### Il flusso completato come arrivo: si chiude il conteggio

Ogni riga di calcolo aperta che arriva a questo flusso si chiude alla sua fine, con:

* i giorni lordi, fra inizio e fine del conteggio (mai negativi);
* i giorni netti, da `pratiche.fn_calcola_tempo_netto_da_a`, al netto delle sospensioni;
* i giorni di sospensione, differenza fra i due;
* `sforato`, vero quando i giorni netti superano quelli previsti dalla formula.

---

### Test

* `pratiche/test-sospensioni-tempi` — apertura e chiusura del conteggio, al netto delle sospensioni.

---

{% include-markdown "signature-core.md" %}
