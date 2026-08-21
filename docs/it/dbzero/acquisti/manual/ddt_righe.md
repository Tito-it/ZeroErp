## 📘 Documentazione Concettuale – Tabella `acquisti.ddt_righe`

> 👀 **Vedi anche**
>
> • [acquisti.ddt](/dbzero/acquisti/tabelle/ddt)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Le righe del DDT di acquisto**: la merce effettivamente ricevuta.

Sono il punto in cui il magazzino dovrebbe essere caricato — la causale prevista è
`CARICO_ACQ` (segno +1, impatto `cmp` sulla valorizzazione).

⚠️ **Oggi quel collegamento non esiste**: `magazzino.movimenti` è vuota e nessun verbo lega la
ricezione al carico. È la giunzione fra i due domini predisposti, e va costruita quando
entrambi entreranno in esercizio.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
