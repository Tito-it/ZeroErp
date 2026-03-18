## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_ful_guard_consistenza()`

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

### Utilizzo

Viene invocata da trigger `BEFORE INSERT/UPDATE` su
`vendite.ordini_righe_fulfillment` come guardia di integrità transazionale.

---

{% include-markdown "signature-core.md" %}
