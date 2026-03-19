## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_preventivi_gen_codice()`

> 👀 **Vedi anche**
>
• [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)  
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)  

---
### 🎯 Scopo Principale
La trigger function `vendite.trgfn_preventivi_gen_codice()` genera
automaticamente `numero` preventivo quando il campo non viene valorizzato.

---

### Regole principali

* se `NEW.numero` e` nullo/vuoto, valorizza con `script.fn_generate_codice('preventivo')`;
* se `NEW.numero` e` gia` presente, non interviene.

---

### Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.preventivi` per garantire una
numerazione coerente anche in inserimenti batch/automatici.

---

{% include-markdown "signature-core.md" %}
