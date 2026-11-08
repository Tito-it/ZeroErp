## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_allegati_pratiche_giornale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove scrive
> * [pratiche.allegati_pratiche](/dbzero/pratiche/tabelle/allegati_pratiche) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_allegati_flussi_giornale](/dbzero/pratiche/funzioni/trgfn_allegati_flussi_giornale) — la gemella per gli allegati di un flusso

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_allegati_pratiche_giornale` registra nel giornale l'aggiunta di
un allegato a una pratica, con l'azione `ALLEGATO_AGGIUNTO`.

---

### Che cosa scrive

Scatta `AFTER INSERT` su `pratiche.allegati_pratiche` e scrive una riga di `pratiche.giornale` per la
pratica, senza flusso (l'allegato è della pratica, non di un passo), con origine `SISTEMA`. Il
dettaglio porta l'id dell'allegato, il suo tipo e il nome del file.

`pratiche.allegati_pratiche` non ha una colonna di transazione, e la funzione non ne passa una: la
riga del giornale riceve la transazione della sessione dal trigger di `tx_id` del giornale.

---

{% include-markdown "signature-core.md" %}
