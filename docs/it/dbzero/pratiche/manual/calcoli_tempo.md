## 📘 Documentazione Concettuale – Tabella `pratiche.calcoli_tempo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.formule_tempo](/dbzero/pratiche/tabelle/formule_tempo) — la regola da cui nasce il conteggio
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — i due flussi fra cui si misura il tempo
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — i periodi che non contano
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica del conteggio
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_calcolo_tempo_completamento](/dbzero/pratiche/funzioni/trgfn_flussi_calcolo_tempo_completamento) — l'unico scrittore: apre e chiude il conteggio
> * [pratiche.trgfn_calcoli_tempo_guard_immutabili](/dbzero/pratiche/funzioni/trgfn_calcoli_tempo_guard_immutabili) — protegge le colonne che non cambiano
> * [pratiche.trgfn_calcoli_tempo_set_periodo](/dbzero/pratiche/funzioni/trgfn_calcoli_tempo_set_periodo) — tiene allineato il periodo
> * [pratiche.fn_calcola_tempo_netto_da_a](/dbzero/pratiche/funzioni/fn_calcola_tempo_netto_da_a) · [pratiche.fn_valuta_tempo_esecuzione_da_a](/dbzero/pratiche/funzioni/fn_valuta_tempo_esecuzione_da_a) — il calcolo al volo, senza leggere questa tabella
>
> Guide:
>
> * [Gestione pratiche](/guide/gestione-pratiche) — il modello delle pratiche

---

### 🎯 Scopo Principale

La tabella `pratiche.calcoli_tempo` conserva la misura del tempo impiegato, in una pratica, dal
completamento di un flusso di partenza al completamento di un flusso di arrivo, secondo una formula di
`pratiche.formule_tempo`: una riga per pratica, coppia di flussi e formula.

---

### Il ciclo di vita di un conteggio

La tabella la scrive solo `pratiche.trgfn_flussi_calcolo_tempo_completamento`, al completamento di un
flusso:

1. **Apertura** — il flusso di partenza si completa: nasce la riga, con l'inizio del conteggio (la fine
   del flusso di partenza) e la fotografia dei giorni previsti dalla formula.
2. **Chiusura** — il flusso di arrivo si completa: la riga riceve la fine del conteggio e i giorni
   calcolati.
3. **Ordine invertito** — se il flusso di arrivo è già completato quando si completa quello di
   partenza, la riga nasce e si chiude subito.

Mentre il conteggio è aperto, la fine e i giorni sono vuoti.

⚠️ Inizio e fine del conteggio si leggono da `pratiche.flussi.data_fine`, e l'inizio è obbligatorio.
Nessuna funzione del database valorizza `data_fine` quando un flusso si completa (né il completamento
automatico di `pratiche.fn_reconcile_sorgente`): il conteggio regge solo se chi completa il flusso la
scrive nella stessa istruzione.

---

### Le colonne che non si capiscono dal nome

* `giorni_formula` — la fotografia di `formule_tempo.giorni_esecuzione` all'apertura: una modifica
  successiva della formula non cambia i conteggi già aperti.
* `giorni_lordi`, `giorni_sospensione`, `giorni_netti` — i giorni di calendario del periodo, quelli di
  sospensione che vi ricadono, e la differenza.
* `sforato` — i giorni netti superano quelli previsti dalla formula.
* `periodo_calcolo` — lo stesso intervallo come range di istanti, chiuso a sinistra e aperto a destra,
  illimitato finché il conteggio è aperto. Lo calcola il trigger dalle due date: si interroga per
  appartenenza di un istante.

---

### ⛔ Che cosa non cambia

Pratica, flussi, formula, giorni previsti e inizio del conteggio sono fissati all'apertura:
`pratiche.trgfn_calcoli_tempo_guard_immutabili` rifiuta un aggiornamento che li tocca. Si aggiornano
solo la fine, i giorni calcolati, `sforato` e le colonne tecniche.

I vincoli di tabella tengono il resto: la fine segue l'inizio, i giorni previsti sono positivi, i due
flussi sono diversi, e la stessa coppia di flussi con la stessa formula ha un solo conteggio per
pratica. La formula deve essere attiva, e una formula con conteggi non si disattiva.

---

### Chi legge

Nessuna funzione del database legge questa tabella: `pratiche.fn_calcola_tempo_netto_da_a` e
`pratiche.fn_valuta_tempo_esecuzione_da_a` ricalcolano dai flussi e dalle sospensioni. La tabella è la
misura conservata, per il backend e i report. La visibilità segue la pratica: la regola RLS limita le
righe al perimetro di emittente dell'operatore.

---

### Test

* `pratiche/test-sospensioni-tempi` — apertura e chiusura del conteggio, sottrazione delle sospensioni e
  guard delle colonne immutabili.

---

{% include-markdown "signature-core.md" %}
