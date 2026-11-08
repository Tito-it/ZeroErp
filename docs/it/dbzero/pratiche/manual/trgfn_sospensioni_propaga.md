## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_propaga`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la sospensione che scatena la propagazione
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — i flussi che passano a `SOSPESO`
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — gli stati del flusso
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_riattiva](/dbzero/pratiche/funzioni/trgfn_sospensioni_riattiva) — il verso opposto, alla chiusura della sospensione

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_sospensioni_propaga` porta a `SOSPESO` i flussi attivi di una
pratica quando nasce una sospensione dell'intera pratica.

---

### La regola

* Scatta dopo l'inserimento di una riga in `pratiche.sospensioni`.
* Agisce solo sulle sospensioni di pratica (`flusso_id` vuoto): una sospensione di un solo flusso non
  si propaga.
* I flussi della pratica in `DA_ESEGUIRE` o `IN_CORSO` passano a `SOSPESO`; quelli già chiusi o già
  sospesi restano come sono.

⭐ La funzione non salva lo stato di partenza dei flussi: il cambio di stato lo registra il giornale
del flusso, ed è da lì che `pratiche.trgfn_sospensioni_riattiva` ritrova lo stato da ripristinare
quando la sospensione si chiude.

---

{% include-markdown "signature-core.md" %}
