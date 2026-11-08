## 📘 Documentazione Concettuale – Funzione `pratiche.fn_calcola_tempo_netto_da_a`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — le date di fine dei due flussi
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — i periodi che si sottraggono
> * [pratiche.calcoli_tempo](/dbzero/pratiche/tabelle/calcoli_tempo) — dove il tempo calcolato si registra
>
> Approfondimento funzioni:
>
> * [pratiche.fn_valuta_tempo_esecuzione_da_a](/dbzero/pratiche/funzioni/fn_valuta_tempo_esecuzione_da_a) — confronta questi giorni con la formula

---

### 🎯 Scopo Principale

`pratiche.fn_calcola_tempo_netto_da_a` è un controllo puro che calcola i giorni netti trascorsi fra la fine
di un flusso di partenza e la fine di un flusso di arrivo, togliendo i periodi in cui la pratica è stata
sospesa.

---

### Il calcolo

* La partenza è la data di fine del flusso di partenza. Se il flusso non è ancora finito, la funzione
  restituisce un valore vuoto: non c'è niente da misurare.
* L'arrivo è la data di fine del flusso di arrivo; se non c'è ancora, è adesso.
* I giorni lordi sono i giorni interi fra partenza e arrivo.
* Si tolgono i giorni interi delle sospensioni **a livello di pratica** che cadono nel periodo, ciascuna
  ritagliata sul periodo; una sospensione ancora aperta conta fino ad adesso. Le sospensioni di un solo
  flusso non si sottraggono.
* Il risultato non scende mai sotto zero.

---

{% include-markdown "signature-core.md" %}
