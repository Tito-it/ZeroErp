## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_riattiva`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la sospensione che si chiude
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — da dove si legge lo stato che un flusso aveva prima
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — i flussi che tornano al loro stato
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_propaga](/dbzero/pratiche/funzioni/trgfn_sospensioni_propaga) — l'andata: la sospensione della pratica sospende i flussi attivi
> * [pratiche.trgfn_flussi_giornale_stato](/dbzero/pratiche/funzioni/trgfn_flussi_giornale_stato) — scrive nel giornale lo stato precedente che qui si rilegge

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_sospensioni_riattiva` riattiva una pratica quando la sua
sospensione si chiude: la pratica torna `APERTA` e ogni flusso `SOSPESO` torna allo stato che aveva
prima della sospensione.

---

### Quando scatta

Scatta dopo l'aggiornamento della data di fine di una sospensione, solo quando la data passa da vuota
a valorizzata: è la chiusura della sospensione. Una sospensione di un singolo flusso (con `flusso_id`)
non riattiva niente: la regola vale solo per le sospensioni dell'intera pratica.

---

### ⭐ Lo stato precedente si legge dal giornale

La sospensione non conserva lo stato da cui ogni flusso è partito: lo conserva il giornale. Per ogni
flusso ancora `SOSPESO`, la funzione cerca l'ultimo cambio di stato registrato (`FLUSSO_STATO_CAMBIATO`)
che ha portato il flusso a `SOSPESO`, e lo riporta allo stato di partenza di quel cambio.

⚠️ Un flusso `SOSPESO` senza quel passaggio nel giornale resta `SOSPESO`: senza lo stato di partenza
non c'è niente da ripristinare.

Il ritorno allo stato precedente è un normale cambio di stato del flusso: passa dai guard di
transizione dei flussi e lascia la sua riga nel giornale, come qualunque altro cambio.

---

{% include-markdown "signature-core.md" %}
