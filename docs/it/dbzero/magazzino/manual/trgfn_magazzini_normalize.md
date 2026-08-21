## 📘 Documentazione Concettuale – Funzione `magazzino.trgfn_magazzini_normalize()`

> 👀 **Vedi anche**
>
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Normalizza il **codice del magazzino**: `upper(btrim(...))`.

Due righe di codice, un effetto concreto: `mag1`, `MAG1 ` e ` Mag1` diventano lo stesso
codice, e l'unicità del codice smette di dipendere da come è stato digitato.

⚠️ Agisce **solo se `codice` non è nullo**, e non impone che lo sia: l'obbligatorietà la dà il
vincolo di colonna, non questo trigger.

---

### ⭐ Perché normalizzare all'ingresso e non in lettura

Perché il confronto avvenga sempre sulla stessa forma. Normalizzare in lettura significa
ricordarsene a ogni query — e basta dimenticarlo una volta perché due magazzini «diversi»
risultino uguali, o viceversa.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
