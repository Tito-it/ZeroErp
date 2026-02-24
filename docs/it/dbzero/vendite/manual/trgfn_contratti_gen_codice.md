## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_gen_codice()`

> 👀 **Vedi anche**
>
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)  
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)  

---

### 🎯 Scopo Principale

La trigger function `vendite.trgfn_contratti_gen_codice()` genera automaticamente
`numero` contratto quando il valore non viene fornito.

---

### ✅ Regole principali

* se `NEW.numero` e` nullo/vuoto, valorizza con `script.fn_generate_codice('contratto')`;
* se `NEW.numero` e` gia` presente, non modifica il valore.

---

### 🧩 Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.contratti` per garantire
numerazione tecnica consistente anche in inserimenti automatici.

---

{% include-markdown "signature-core.md" %}
