## 📘 Documentazione Concettuale – Funzione `pratiche.fn_lista_pratiche_per_contesto`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — le pratiche e il loro contesto anagrafico
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo del soggetto, prima lente
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza utility, seconda lente
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_pratiche_guard_contesto](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_contesto) — la coerenza fra soggetto, ruolo e istanza su cui le lenti si appoggiano
> * [pratiche.fn_coda_lavoro_operatore](/dbzero/pratiche/funzioni/fn_coda_lavoro_operatore) — la coda dell'operatore, che il contesto non lo guarda
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — la generazione fra pratiche, che propaga il contesto

---

### 🎯 Scopo Principale

La funzione `pratiche.fn_lista_pratiche_per_contesto` è la lente canonica del contesto anagrafico:
il punto unico da cui passa ogni elenco «pratiche di X» dell'applicazione, per un emittente.

Nessuna vista applicativa ricostruisce il filtro per conto suo.

---

### Tre lenti, al massimo una per volta

* **Pratiche del ruolo** — le pratiche di un ruolo di soggetto (per esempio il ruolo cliente, nel
  drawer del cliente).
* **Pratiche dell'istanza** — le pratiche di un'istanza utility (per esempio un contatore).
* **Pratiche interne** — quelle senza soggetto, cioè senza contesto cliente; il guard del contesto
  garantisce che una pratica senza soggetto non abbia nemmeno ruolo né istanza.

Senza nessuna lente, la funzione restituisce tutte le pratiche dell'emittente. Le lenti sono
alternative: chiederne più d'una nella stessa chiamata è un errore, non un'intersezione.

L'emittente è obbligatorio: è la separazione fra aziende.

---

### Il contesto di ogni pratica

La colonna `contesto` dà a ogni pratica un solo valore, per il raggruppamento a video, in ordine di
precedenza: `RUOLO` se ha un ruolo di soggetto, altrimenti `ISTANZA` se ha un'istanza utility,
altrimenti `SOGGETTO` se ha solo il soggetto, altrimenti `INTERNA`.

`stato_codice` e `priorita_codice` sono i codici interni dello stato e della priorità.

L'ordine è per priorità (dalla più alta), poi per scadenza (quelle senza scadenza in fondo), poi per
id.

---

### Da sapere

* La coda di lavoro dell'operatore non guarda il contesto, per scelta di modello: la coda è per
  operatore, il contesto è per cliente.
* La generazione fra pratiche propaga ruolo e istanza alla pratica figlia: le pratiche generate cadono
  nelle lenti giuste.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — emittente assente o non positivo.
* `E_PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI` — più di una lente nella stessa chiamata.

---

### Test

* `pratiche/test-lista-pratiche-contesto` — le tre lenti, il valore di `contesto` e l'esclusività
  delle lenti.

---

{% include-markdown "signature-core.md" %}
