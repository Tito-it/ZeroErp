## 📘 Documentazione Concettuale – Funzione `dbops.fn_normalize_indirizzo`

> 👀 **Vedi anche**
>
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
> • [script.fn_norm_via](/dbzero/script/funzioni/fn_norm_via)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Prende un **indirizzo scritto a mano** («Via Roma 10») e un comune, e prova a risolverlo in
un indirizzo strutturato: via normalizzata, civico, CAP, geolocalizzazione.

⚠️ **È dichiaratamente una base.** Il commento nel corpo lo dice: la stringa reale sarà più
complessa — `'Via Roma 10/e batt.4 int.7 piano 4'` — e le eccezioni andranno aggiunte. Va
usata sapendo che i casi non banali non li copre.

⭐ La conseguenza pratica: **il risultato va verificato, non dato per buono**. Un indirizzo che
non risolve è più utile di uno risolto male, perché il secondo entra in anagrafica e ci resta.

---

{% include-markdown "signature-core.md" %}
