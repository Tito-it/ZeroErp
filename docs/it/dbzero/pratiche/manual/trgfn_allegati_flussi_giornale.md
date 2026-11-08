## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_allegati_flussi_giornale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove scrive
> * [pratiche.allegati_flussi](/dbzero/pratiche/tabelle/allegati_flussi) — la tabella su cui è montata
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — da cui legge la pratica
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_allegati_pratiche_giornale](/dbzero/pratiche/funzioni/trgfn_allegati_pratiche_giornale) — la gemella per gli allegati della pratica

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_allegati_flussi_giornale` registra nel giornale l'aggiunta di un
allegato a un flusso, con l'azione `ALLEGATO_AGGIUNTO`.

---

### Che cosa scrive

Scatta `AFTER INSERT` su `pratiche.allegati_flussi`. L'allegato conosce solo il flusso: la pratica si
legge dal flusso, e la riga di `pratiche.giornale` porta entrambi, con origine `SISTEMA`. Il dettaglio
porta l'id dell'allegato, il suo tipo e il nome del file.

`pratiche.allegati_flussi` non ha una colonna di transazione, e la funzione non ne passa una: la riga
del giornale riceve la transazione della sessione dal trigger di `tx_id` del giornale.

---

{% include-markdown "signature-core.md" %}
