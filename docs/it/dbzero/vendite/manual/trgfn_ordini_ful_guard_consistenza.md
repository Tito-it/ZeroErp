## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_ful_guard_consistenza()`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
• [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)  
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)  
> • [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)  

---
### 🎯 Scopo Principale
La trigger function `vendite.trgfn_ordini_ful_guard_consistenza()` protegge la
coerenza delle righe fulfillment ordine↔DDT e impedisce over-fulfillment.

---

### Regole principali

* `qta_evasa` deve essere `> 0`;
* blocca in lock la riga ordine e il gruppo fulfillment della stessa riga per
  serializzare aggiornamenti concorrenti;
* verifica esistenza delle righe collegate (`ordine_riga_id`, `ddt_riga_id`);
* impone match articolo tra riga ordine e riga DDT;
* impone match UOM quando entrambe valorizzate;
* calcola il residuo ordine e blocca quantità evasa che lo supera.

---

### L'onere passa intero (rev 2026-11-03)

Punto 5-ter (`20261103-37`, brief-db-addebito-trasporto-ordine §8.2): se la riga d'ordine è un onere
(`script.fn_natura_e_merce` falso sulla natura congelata) il legame porta la sua quantità **intera**,
altrimenti `E_ORD_FUL_ONERE_NON_INTERO` (campo `qta_evasa`; nella frase numero di riga, ordine e le due
quantità). Vale per ogni porta che scrive il legame: la copia ordine → bolla, un legame a mano, la
correzione della quantità evasa. Sta prima del residuo: una seconda copia intera la ferma
`E_QTA_SUPERA_RESIDUO`, una parziale il 5-ter.

---

### Utilizzo

Viene invocata da trigger `BEFORE INSERT/UPDATE` su
`vendite.ordini_righe_fulfillment` come guardia di integrità transazionale.

---

{% include-markdown "signature-core.md" %}
