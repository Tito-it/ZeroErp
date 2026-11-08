## 📘 Documentazione Concettuale – Tabella `pratiche.formule_tempo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) — il tipo di prestazione a cui la formula si applica
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — i due template fra cui si misura il tempo
> * [pratiche.calcoli_tempo](/dbzero/pratiche/tabelle/calcoli_tempo) — i conteggi nati dalla formula
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_calcolo_tempo_completamento](/dbzero/pratiche/funzioni/trgfn_flussi_calcolo_tempo_completamento) — apre i conteggi sulle formule attive
> * [pratiche.fn_valuta_tempo_esecuzione_da_a](/dbzero/pratiche/funzioni/fn_valuta_tempo_esecuzione_da_a) — valuta il tempo di una pratica rispetto alla formula
> * [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — congela la formula con la sua edizione
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) — la copia in una nuova edizione
>
> Guide:
>
> * [Configurazione delle pratiche](/guide/gestione-pratiche-configurazione) — tipi di prestazione, template e tempi

---

### 🎯 Scopo Principale

La tabella `pratiche.formule_tempo` definisce il tempo massimo di esecuzione fra due step di un tipo di
prestazione: dal completamento del flusso di partenza al completamento del flusso di arrivo, con le
soglie di avviso e di criticità.

È configurazione, non dato operativo: i conteggi veri stanno in `pratiche.calcoli_tempo`.

---

### Le soglie

* `giorni_esecuzione` — il tempo massimo previsto, al netto delle sospensioni.
* `giorni_warning` e `giorni_critico` — le soglie dei giorni rimanenti a cui la situazione diventa
  d'avviso e poi critica.

I vincoli tengono l'ordine: tutti e tre sono positivi, l'avviso scatta prima del critico e cade dentro
il tempo massimo. I due template sono diversi, e per un tipo di prestazione la stessa coppia di
template ha una sola formula.

---

### Chi la usa

* Quando un flusso si completa, `pratiche.trgfn_flussi_calcolo_tempo_completamento` cerca le formule
  **attive** dello stesso tipo di prestazione che partono dal suo template, e apre il conteggio. Al
  conteggio passa la fotografia di `giorni_esecuzione`: cambiarla dopo non tocca i conteggi aperti.
* `pratiche.fn_valuta_tempo_esecuzione_da_a` la legge per valutare una pratica al volo.

Il tipo di prestazione e i due template devono essere attivi, e una formula che ha conteggi non si
disattiva.

---

### ⛔ La formula segue la sua edizione

La formula appartiene all'edizione di workflow del template di partenza.
`pratiche.trgfn_template_flussi_figli_guard_immutabile` rifiuta, con `E_TEMPLATE_DEFINIZIONE_CONGELATA`,
l'inserimento o la modifica di una formula su un'edizione con la struttura bloccata (pubblicata o
ritirata), e la cancellazione su un'edizione pubblicata. Per cambiare una formula si lavora su una
nuova edizione, in cui `pratiche.fn_copia_definizione` la ricopia rimappando i template.

---

### Codici errore

* `E_TEMPLATE_DEFINIZIONE_CONGELATA` — modifica di una formula di un'edizione bloccata.

---

### Test

* `pratiche/test-sospensioni-tempi` — la formula apre e chiude i conteggi.
* `pratiche/test-definizione-ritirata-edit-freeze` e `pratiche/test-fork-chiusura-per-definizione` —
  il congelamento con l'edizione e la copia in una nuova edizione.

---

{% include-markdown "signature-core.md" %}
