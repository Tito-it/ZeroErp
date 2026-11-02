## 📘 Documentazione Concettuale – Trigger function `magazzino.trgfn_magazzini_normalize`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — la tabella su cui è montato

---

### 🎯 Scopo Principale

Normalizza il **codice del magazzino** all'inserimento e all'aggiornamento: toglie gli spazi in
testa e in coda e lo porta in maiuscolo.

Un effetto concreto: «mag1», «MAG1» con uno spazio in coda e «Mag1» con uno spazio in testa
diventano lo stesso codice, e l'unicità del
codice smette di dipendere da come è stato digitato.

⚠️ Agisce **solo se il codice c'è**, e non impone che ci sia: l'obbligatorietà la dà il
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
