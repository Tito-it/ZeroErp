## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_preventivi_normalize()`

> 👀 **Vedi anche**
>
> • [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)  

---

### 🎯 Scopo Principale

La trigger function `vendite.trgfn_preventivi_normalize()` completa i dati
minimi di data documento in insert quando il numero preventivo e` gia` presente.

---

### ✅ Regole principali

* su `INSERT`, se `numero` e` valorizzato e `data` e` nulla:
  * imposta `data = CURRENT_DATE`;
* non modifica `data` quando gia` valorizzata.

---

### 🧩 Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.preventivi` per ridurre casi di
record parziali in creazione tecnica/automatica.

---

{% include-markdown "signature-core.md" %}
