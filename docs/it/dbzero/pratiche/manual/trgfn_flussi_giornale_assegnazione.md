## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_giornale_assegnazione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso riassegnato
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si scrive l'evento
>
> Approfondimento funzioni:
>
> * [pratiche.fn_prendi_in_carico_flusso](/dbzero/pratiche/funzioni/fn_prendi_in_carico_flusso) — la presa in carico, che cambia l'assegnatario
> * [pratiche.trgfn_pratiche_giornale_assegnazione](/dbzero/pratiche/funzioni/trgfn_pratiche_giornale_assegnazione) — la stessa regola sulla pratica

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_giornale_assegnazione` scrive nel giornale l'azione
`FLUSSO_ASSEGNAZIONE_CAMBIATA` a ogni cambio di assegnazione di un singolo flusso: l'operatore, il
reparto o entrambi.

È lo specchio, a livello di flusso, di `pratiche.trgfn_pratiche_giornale_assegnazione`.

---

### Le regole

* Scatta dopo l'aggiornamento del flusso, e solo se almeno una delle due colonne di assegnazione
  cambia davvero: il giornale non riceve righe a vuoto.
* La riga è della pratica e del flusso; il dettaglio porta la risorsa umana e l'unità organizzativa,
  prima e dopo.
* Ogni strada che cambia l'assegnatario lascia la sua riga: la presa in carico
  (`pratiche.fn_prendi_in_carico_flusso`) come l'assegnazione esplicita del backend.
* La transazione della riga è quella del flusso.

⭐ **L'origine è `UTENTE`, non `SISTEMA`** come sulla pratica: l'assegnazione di un flusso la compie un
operatore. Un'assegnazione automatica, quando ci sarà, si distinguerà con `SISTEMA`.

L'utente che ha agito non lo scrive questa funzione: lo mette l'audit della tabella del giornale,
dall'identità della sessione.

---

### Test

* `pratiche/test-assegnazione-flusso-eligibilita` — la riassegnazione e la presa in carico lasciano
  la riga di giornale.

---

### Note di migrazione

* 2026-06-18 — nasce: prima il giornale tracciava solo l'assegnazione della pratica
  (brief-db-assegnazione-flusso).

---

{% include-markdown "signature-core.md" %}
