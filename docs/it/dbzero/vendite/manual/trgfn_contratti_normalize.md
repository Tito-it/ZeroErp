## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_normalize()`

> 👀 **Vedi anche**
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)  

---
### 🎯 Scopo Principale
La trigger function `vendite.trgfn_contratti_normalize()` completa i dati
minimi del contratto in insert quando il numero documento e` presente.

---

### Regole principali

* su `INSERT`, se `numero` e` valorizzato e `data` e` nulla:
  * imposta `data = CURRENT_DATE`;
* non modifica `data` quando gia` valorizzata.

---

### Utilizzo

Usata come trigger `BEFORE INSERT` su `vendite.contratti` per evitare
documenti con numerazione presente ma data mancante.

---

{% include-markdown "signature-core.md" %}
