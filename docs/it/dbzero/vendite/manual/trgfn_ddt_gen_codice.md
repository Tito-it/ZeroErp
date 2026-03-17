## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_gen_codice()`

> 👀 **Vedi anche**
>
• [vendite.ddt](/dbzero/vendite/tabelle/ddt)  
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)  

---

### 🎯 Scopo Principale

La trigger function `vendite.trgfn_ddt_gen_codice()` genera automaticamente
`numero` DDT quando il valore non viene fornito in inserimento.

---

### Regole principali

* se `NEW.numero` e` nullo/vuoto, valorizza con `script.fn_generate_codice('ddt')`;
* se `NEW.numero` e` gia` presente, non interviene.

---

### Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.ddt` per garantire numerazione
tecnica coerente anche in creazioni automatiche.

---

{% include-markdown "signature-core.md" %}
