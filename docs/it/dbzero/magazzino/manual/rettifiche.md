## 📘 Documentazione Concettuale – Tabella `magazzino.rettifiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe)
> • [magazzino.inventari](/dbzero/magazzino/tabelle/inventari)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Documento interno di **rettifica inventariale**: la correzione formale di una differenza.

---

### Il ruolo nella catena

È il ponte fra il conteggio e il ledger: le sue righe diventano movimenti con causale `RETT_POS` o `RETT_NEG`, entrambe a impatto `cmp` — una rettifica **cambia il valore di magazzino**, non solo la quantità.

---

### ⚠️ Testata e righe

Il dettaglio sta in `magazzino.rettifiche_righe`. Le due tabelle vanno lette insieme: la testata porta il contesto (data, magazzino, stato), le righe le quantità.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
