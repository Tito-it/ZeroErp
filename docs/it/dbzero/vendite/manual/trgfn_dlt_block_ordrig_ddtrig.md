## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_dlt_block_ordrig_ddtrig()`

> 👀 **Vedi anche**
>
• [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)  
> • [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)  
> • [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)  

---

### 🎯 Scopo Principale

La trigger function `vendite.trgfn_dlt_block_ordrig_ddtrig()` blocca la
cancellazione fisica di righe ordine/DDT per preservare la coerenza del
fulfillment e la tracciabilità operativa.

---

### Regole principali

* su `vendite.ordini_righe`:
  * se esistono righe in `ordini_righe_fulfillment` collegate, errore `E_DELETE_BLOCKED_FUL`;
  * altrimenti errore `E_DELETE_NOT_ALLOWED` (delete logico preferito).
* su `vendite.ddt_righe`:
  * stessa regola di blocco in presenza di fulfillment collegato;
  * altrimenti delete comunque non consentito.
* su tabelle non previste, genera errore di delete non consentito.

---

### Utilizzo

Usata come trigger `BEFORE DELETE` per impedire delete distruttivi su righe
documento con o senza fulfillment, forzando processi di annullamento gestiti.

---

{% include-markdown "signature-core.md" %}
