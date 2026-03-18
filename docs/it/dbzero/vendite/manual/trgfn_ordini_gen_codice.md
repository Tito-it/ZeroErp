## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_gen_codice()`

> 👀 **Vedi anche**
>
• [vendite.ordini](/dbzero/vendite/tabelle/ordini)  
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)  

---
### 🎯 Scopo Principale
La trigger function `vendite.trgfn_ordini_gen_codice()` genera automaticamente
`numero` ordine quando il campo non viene fornito.

---

### Regole principali

* se `NEW.numero` e` nullo/vuoto, valorizza con `script.fn_generate_codice('ordine')`;
* se `NEW.numero` e` gia` presente, non modifica il valore.

---

### Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.ordini` per garantire numerazione
tecnica consistente anche in inserimenti automatici.

---

{% include-markdown "signature-core.md" %}
