## 📘 Documentazione Concettuale – Funzione `pratiche.fn_check_pratica_chiudibile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_chiusura_pratica](/dbzero/pratiche/funzioni/fn_check_chiusura_pratica) — gli step obbligatori ancora bloccanti
> * [pratiche.fn_pratica_flussi_aperti](/dbzero/pratiche/funzioni/fn_pratica_flussi_aperti) — i flussi istanziati non ancora terminali
> * [pratiche.trgfn_flussi_autochiusura_pratica](/dbzero/pratiche/funzioni/trgfn_flussi_autochiusura_pratica) — la chiusura automatica
> * [pratiche.trgfn_flussi_guard_chiusura_prematura](/dbzero/pratiche/funzioni/trgfn_flussi_guard_chiusura_prematura) — il guard sul completamento del flusso di chiusura
> * [pratiche.trgfn_pratiche_guard_chiusura_flussi](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_chiusura_flussi) — il guard sulla chiusura manuale

---

### 🎯 Scopo Principale

`pratiche.fn_check_pratica_chiudibile` risponde «la pratica è chiudibile?», cioè «non ha più lavoro da
fare?». È un controllo puro: risponde vero o falso e non solleva errori.

---

### Le due condizioni, entrambe necessarie

* **Nessuno step obbligatorio bloccante**, secondo `pratiche.fn_check_chiusura_pratica`: obbligatorio,
  non completato e ancora percorribile. Il ramo morto di un bivio non blocca.
* **Nessun flusso istanziato in uno stato non terminale**, secondo `pratiche.fn_pratica_flussi_aperti`:
  il lavoro avviato e non finito blocca anche se lo step non è obbligatorio.

⭐ **Un predicato, tre chiamanti.** La chiusura automatica (`pratiche.trgfn_flussi_autochiusura_pratica`),
il guard sul completamento del flusso di chiusura (`pratiche.trgfn_flussi_guard_chiusura_prematura`) e
il guard sulla chiusura manuale (`pratiche.trgfn_pratiche_guard_chiusura_flussi`) leggono la stessa
regola, così le tre strade non divergono.

---

### Le due esclusioni

I due parametri facoltativi servono al guard sul completamento del flusso di chiusura: quando il guard
gira, quel flusso non è ancora completato, e senza esclusioni bloccherebbe sé stesso.

* l'esclusione di uno **step di template** lo toglie dagli obbligatori bloccanti;
* l'esclusione di un **flusso** lo toglie dai flussi aperti.

Senza esclusioni la funzione valuta la pratica intera.

---

### Test

* `pratiche/test-chiusura-nessun-lavoro-pendente` — il ramo morto di un bivio non blocca, un flusso
  avviato e non finito sì.
* `pratiche/test-autochiusura-pratica` — la chiusura automatica nei due modelli di pratica.

---

### Note di migrazione

* 2026-07-01 — la condizione sui flussi istanziati non terminali si è aggiunta a quella sugli obbligatori, col suo
  parametro di esclusione in coda; la chiamata con i soli primi due argomenti resta valida
  (brief-db-chiusura-pratica-nessun-lavoro-pendente).

---

{% include-markdown "signature-core.md" %}
