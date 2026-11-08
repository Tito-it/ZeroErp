## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_giornale_stato`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso che cambia stato
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si scrive l'evento
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_riattiva](/dbzero/pratiche/funzioni/trgfn_sospensioni_riattiva) — rilegge questo evento per ripristinare lo stato di un flusso sospeso

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_giornale_stato` scrive nel giornale l'azione
`FLUSSO_STATO_CAMBIATO` a ogni cambio di stato di un flusso.

---

### La regola

* Scatta dopo l'aggiornamento dello stato del flusso, e solo se lo stato cambia davvero.
* La riga del giornale è della pratica e del flusso, con origine `SISTEMA`; il dettaglio porta lo stato
  precedente, lo stato nuovo e l'esito del flusso in quel momento.
* La transazione della riga è quella del flusso; se manca, quella della sessione.

⭐ **L'evento è anche una memoria.** Lo stato precedente scritto qui è ciò che
`pratiche.trgfn_sospensioni_riattiva` rilegge per riportare un flusso sospeso allo stato da cui era
partito; l'esito serve a chi ricostruisce la storia del flusso per generare il lavoro a valle.

---

{% include-markdown "signature-core.md" %}
