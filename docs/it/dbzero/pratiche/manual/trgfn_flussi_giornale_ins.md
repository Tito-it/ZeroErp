## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_giornale_ins`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove scrive
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella su cui è montata

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_giornale_ins` registra nel giornale della pratica la
nascita di un flusso, con l'azione `FLUSSO_CREATO`.

---

### Che cosa scrive

Scatta `AFTER INSERT` su `pratiche.flussi` e scrive una riga di `pratiche.giornale` per la pratica
del flusso e per il flusso stesso, con origine `SISTEMA`. Il dettaglio porta il template da cui il
flusso nasce, lo stato iniziale e la sequenza.

La transazione è quella del flusso; se il flusso non la porta, quella della sessione.

---

### Test

* `pratiche/test-trigger-giornale-flussi` — l'inserimento di un flusso scrive `FLUSSO_CREATO`, col
  dettaglio atteso.

---

{% include-markdown "signature-core.md" %}
