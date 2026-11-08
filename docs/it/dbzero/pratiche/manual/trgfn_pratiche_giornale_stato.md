## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_giornale_stato`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — il diario della pratica, dove finisce la riga
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la tabella su cui scatta il trigger
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_giornale_stato](/dbzero/pratiche/funzioni/trgfn_flussi_giornale_stato) — lo stesso giornale per il cambio di stato di un flusso

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_giornale_stato` scrive nel giornale l'azione
`STATO_CAMBIATO` quando lo stato di una pratica cambia davvero.

---

### La riga di giornale

* È una riga della pratica, non di un flusso: `flusso_id` resta vuoto.
* L'origine è `SISTEMA`: la scrive il database, qualunque sia la strada che ha cambiato lo stato.
* Il dettaglio porta lo stato precedente e il nuovo, per id.
* Il `tx_id` è quello della pratica o, se manca, quello della sessione: la riga di giornale resta
  correlabile alla transazione che ha cambiato lo stato.

Il trigger scatta dopo l'aggiornamento di `stato_id`, e solo quando il valore cambia: riscrivere lo
stesso stato non lascia traccia.

---

### Test

* `pratiche/test-trigger-giornale-pratiche` — il cambio di stato scrive `STATO_CAMBIATO`.

---

{% include-markdown "signature-core.md" %}
