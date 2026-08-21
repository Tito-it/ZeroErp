## 📘 Documentazione Concettuale – Tabella `magazzino.inventari`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe)
> • [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Documento di **conteggio fisico**: la rilevazione di quanto c'è davvero a scaffale.

---

### Il ruolo nella catena

Il conteggio non modifica la giacenza: **produce una rettifica**, che a sua volta produce movimenti. È la catena che tiene il ledger come unica sorgente — anche una correzione da inventario resta una scrittura tracciata, non un ritocco.

---

### ⚠️ Testata e righe

Il dettaglio sta in `magazzino.inventari_righe`. Le due tabelle vanno lette insieme: la testata porta il contesto (data, magazzino, stato), le righe le quantità.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
