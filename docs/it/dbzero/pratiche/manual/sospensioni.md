## 📘 Documentazione Concettuale – Tabella `pratiche.sospensioni`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica sospesa
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso sospeso, o quelli che la sospensione di pratica ferma
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si registrano apertura e chiusura, e da dove la riattivazione rilegge lo stato precedente
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_guard_coerenza_flusso](/dbzero/pratiche/funzioni/trgfn_sospensioni_guard_coerenza_flusso) — il flusso deve appartenere alla pratica
> * [pratiche.trgfn_sospensioni_guard_data_non_futura](/dbzero/pratiche/funzioni/trgfn_sospensioni_guard_data_non_futura) — niente date nel futuro
> * [pratiche.trgfn_sospensioni_set_periodo](/dbzero/pratiche/funzioni/trgfn_sospensioni_set_periodo) — calcola il periodo
> * [pratiche.trgfn_sospensioni_propaga](/dbzero/pratiche/funzioni/trgfn_sospensioni_propaga) · [pratiche.trgfn_sospensioni_riattiva](/dbzero/pratiche/funzioni/trgfn_sospensioni_riattiva) — sospendono e riattivano i flussi
> * [pratiche.fn_calcola_tempo_netto_da_a](/dbzero/pratiche/funzioni/fn_calcola_tempo_netto_da_a) — il tempo netto, che sottrae le sospensioni di pratica

---

### 🎯 Scopo Principale

La tabella `pratiche.sospensioni` registra i periodi di fermo di una pratica intera o di un suo singolo
flusso. Una riga senza `data_fine` è una sospensione ancora aperta.

---

### Pratica o flusso

* `flusso_id` vuoto: la sospensione è dell'intera pratica. All'inserimento, tutti i flussi da eseguire o
  in corso della pratica passano a `SOSPESO`.
* `flusso_id` valorizzato: la sospensione riguarda solo quel flusso, che deve appartenere alla pratica
  della riga.
* Chiudere la sospensione, cioè valorizzare `data_fine`, riattiva i flussi: ciascuno torna allo stato che
  aveva prima, riletto dal giornale.

Apertura e chiusura si registrano nel giornale della pratica.

---

### Le regole del periodo

* `data_fine`, se c'è, è successiva a `data_inizio`.
* Nessuna delle due date può stare nel futuro (con una tolleranza di due minuti per gli orologi).
* `periodo_sospensione` è l'intervallo, chiuso a sinistra e aperto a destra, calcolato dal trigger dalle
  due date: non si scrive a mano.
* Per la stessa pratica, e per lo stesso flusso, i periodi non si sovrappongono: la sospensione di
  pratica e quelle di ogni flusso sono assi separati.
* Una sola sospensione aperta per pratica a livello pratica, e una sola per ciascun flusso.
* `motivo` è obbligatorio.

---

### ⚠️ La riattivazione prevista non fa scattare niente

`data_riattivazione_prevista` è una data che l'operatore dichiara all'apertura. Il database non la
legge: oggi non esiste un processo che chiuda da sé le sospensioni arrivate a quella data. La
riattivazione avviene solo valorizzando `data_fine`.

---

### Perimetro

La tabella ha la RLS: chi legge vede le sospensioni delle pratiche del proprio perimetro. Le modifiche
sono storicizzate.

---

### Codici errore

* `E_SOSPENSIONE_DATA_FUTURA` — una delle due date è nel futuro.
* `E_SOSPENSIONI_FLUSSO_NON_COERENTE` — il flusso non appartiene alla pratica, o non esiste.

---

### Test

* `pratiche/test-sospensioni-anti-overlap-data-futura` — niente sovrapposizioni, niente date future.
* `pratiche/test-sospensioni-tempi` — il periodo calcolato e il tempo netto.
* `rls/test-rls-pratiche-satelliti` — il perimetro.

---

### Note di migrazione

* 2026-06-26 — arriva il divieto di date future.

---

{% include-markdown "signature-core.md" %}
