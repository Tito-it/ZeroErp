## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo del nodo di partenza e la sua chiave (`key_selector`)
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi) — il grafo intero, proiezione «senza seme» degli stessi archi
>
> Approfondimento funzioni:
>
> * [vendite.fn_documento_lineage_archi](/dbzero/vendite/funzioni/fn_documento_lineage_archi) — i passaggi dei soli documenti chiesti: la grammatica degli archi
> * [vendite.fn_documento_lineage_nodi](/dbzero/vendite/funzioni/fn_documento_lineage_nodi) — codice, stato, fase e natura dei nodi toccati
> * [vendite.fn_documento_lineage_legami](/dbzero/vendite/funzioni/fn_documento_lineage_legami) — se il legame di un arco è stato ritirato
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — la sintesi per le liste
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gli errori sui parametri

---

### 🎯 Scopo Principale

`vendite.fn_documento_lineage` percorre la genealogia di un documento per il pannello «Passaggi» del
dettaglio: ritorna la catena degli archi attraversati dal nodo di partenza, con lo stato di ogni tappa
e il livello e l'ordine per renderla a timeline o ad albero.

---

### I parametri

* Il nodo di partenza è la coppia tipo (`config.sorgenti.id`) e chiave del documento in testo, secondo
  il `key_selector` del tipo: `uid` per preventivo e offerta, `id` per gli altri.
* La direzione è `avanti` (dal documento verso le sue destinazioni, per le liste dei documenti) o
  `indietro` (dal documento verso le sue sorgenti, per la lista delle commesse). Il valore predefinito
  è `avanti`.

---

### ⭐ La catena si risale un livello alla volta

La funzione non legge il grafo intero. Parte dal documento e, a ogni livello, chiede a
`vendite.fn_documento_lineage_archi` i passaggi dei soli documenti raggiunti; alla fine legge una volta
i dettagli dei soli nodi toccati da `vendite.fn_documento_lineage_nodi` e il legame di ogni arco da
`vendite.fn_documento_lineage_legami`. Il costo segue la lunghezza della catena, non il numero dei
documenti del sistema.

* Il traversal è un insieme di **percorsi**: un nodo raggiunto per due strade compare due volte,
  ciascuna col suo livello.
* La guardia dei cicli è sul percorso: un nodo già visitato su quel percorso non si riattraversa.
* Si risale al massimo per dieci livelli.
* Un nodo che chi legge non vede esce con le colonne di decorazione vuote: la decorazione è un
  collegamento esterno, e l'arco resta.

---

### Le colonne che non si capiscono dal nome

* `livello` — la profondità dal nodo di partenza (1 = adiacente).
* `ordine` — una sequenza stabile per il rendering: livello, poi gli estremi dell'arco.
* `arco`, `ruolo` — la lettera della relazione (il vocabolario è chiuso e sta in
  `vendite.fn_documento_lineage_archi`) e il ruolo `ROOT` o `COLLEGATO`.
* `is_ramo_inverso` — `true` sui rami di ritorno (per esempio il reso dal DDT, la nota di credito dalla fattura):
  il pannello li rende in modo distinto. Non si ricalcola qui: arriva dalla grammatica degli archi,
  l'unica sede dell'elenco dei rami di ritorno.
* `from_natura_doc_codice_interno`, `to_natura_doc_codice_interno` — la natura del documento fiscale:
  distinguono la fattura dalla nota di credito che la rettifica, due nodi che altrimenti hanno stesso
  tipo, stesso stato e nessun codice finché non sono numerati.
* `is_legame_ritirato` — il **legame** dell'arco, non il nodo: `true` quando quello che il documento ha
  portato dall'altra parte non c'è più, anche se i due documenti sono vivi (dal preventivo annullato la
  commessa resta viva, ma le righe che il preventivo le aveva portato sono annullate). Vale nei due
  versi, perché è dell'arco; vuoto su un arco che il decoratore non censisce. Il passaggio resta come
  storia: si ritira il legame, non il passaggio.

⚠️ **Una conseguenza, per chi rende a video.** Camminando in avanti da una commessa, la nota di credito
compare due volte: come figlia diretta della commessa e, al livello 2, come rettifica della fattura.
Non è un difetto: sono due relazioni diverse verso lo stesso documento, e la funzione ritorna archi,
non nodi.

---

### Sicurezza

La funzione è `STABLE` e `SECURITY INVOKER`: gira coi permessi di chi la chiama, e la visibilità per
emittente dei documenti resta applicata a ogni passo.

---

### Codici errore

* `E_ERRORE_PARAMETRI` — tipo assente o non positivo, chiave assente o vuota, direzione diversa da
  `avanti` e `indietro`.

---

### Test

* `vendite/test-documento-lineage-v1` — forma, `STABLE` e `SECURITY INVOKER`, il vocabolario chiuso
  degli archi e le invarianti del grafo.
* `vendite/test-documento-lineage-seminata-v1` — la risalita per chiave dà gli stessi archi del grafo
  intero.
* `vendite/test-lineage-legame-ritirato-v1` — `is_legame_ritirato` sui percorsi reali.

---

### Note di migrazione

* 2026-08-20 — arrivano le colonne della natura del documento, e `is_ramo_inverso` smette di essere
  ricalcolato qui: con l'arco della nota di credito l'elenco dei rami di ritorno viveva in tre posti.
* 2026-10-10 — la vista degli archi si legge una volta per chiamata, non a ogni livello
  (brief-db-plancache-funzioni-con-query-incorporate).
* 2026-10-11 — la catena si risale per chiave, un livello alla volta, invece di leggere il grafo
  intero; la sintesi per le liste passa da una vista a `vendite.fn_documento_lineage_sintesi`
  (brief-db-lineage-seminata-per-chiave).
* 2026-10-13 — arriva `is_legame_ritirato`, su richiesta del backend dopo un collaudo.

---

{% include-markdown "signature-core.md" %}
