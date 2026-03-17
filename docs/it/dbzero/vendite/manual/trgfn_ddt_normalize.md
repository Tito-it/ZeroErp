## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_normalize()`

> 👀 **Vedi anche**
>
• [vendite.ddt](/dbzero/vendite/tabelle/ddt)  

---

### 🎯 Scopo Principale

La trigger function `vendite.trgfn_ddt_normalize()` completa i campi
temporali minimi del DDT quando il numero documento e` presente.

---

### Regole principali

* su `INSERT`, se `numero` e` valorizzato:
  * imposta `anno` all’anno corrente se nullo/0;
  * imposta `data` a `CURRENT_DATE` se nulla;
* non altera campi gia` valorizzati.

---

### Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.ddt` per evitare documenti
con numerazione presente ma data/anno mancanti.

---

{% include-markdown "signature-core.md" %}
