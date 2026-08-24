## 📘 Documentazione Concettuale – Tabella `acquisti.ddt_indirizzi`

> 👀 **Vedi anche**
>
> • [acquisti.ddt](/dbzero/acquisti/tabelle/ddt)
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Snapshot degli indirizzi** del DDT di acquisto: uno per tipo — tipicamente partenza e
consegna.

⭐ Snapshot e non riferimento: l'indirizzo viene **congelato** sul documento al momento della
registrazione. Se il fornitore trasloca, il DDT continua a dire da dove la merce è
effettivamente partita. È la stessa scelta di tutte le tabelle `*_indirizzi` del progetto, e
la ragione è la ristampa conforme nel tempo.

⚠️ Nota dal commento della tabella: **la mail va inclusa nello snapshot**. È un campo che
serve a valle per le comunicazioni sul documento, e prenderlo dall'anagrafica corrente invece
che dallo snapshot vanificherebbe il congelamento.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
