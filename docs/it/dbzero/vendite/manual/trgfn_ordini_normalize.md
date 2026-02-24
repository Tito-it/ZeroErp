## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_normalize()`

> 👀 **Vedi anche**
>
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini)  

---

### 🎯 Scopo Principale

La trigger function `vendite.trgfn_ordini_normalize()` completa i campi
temporali minimi dell’ordine quando il `numero` e` presente in insert.

---

### ✅ Regole principali

* su `INSERT`, se `numero` e` valorizzato:
  * imposta `anno` all’anno corrente se nullo/0;
  * imposta `data` a `CURRENT_DATE` se nulla;
* non altera i valori se gia` compilati.

---

### 🧩 Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.ordini` per avere record completi
senza richiedere sempre popolamento esplicito di anno/data.

---

{% include-markdown "signature-core.md" %}
