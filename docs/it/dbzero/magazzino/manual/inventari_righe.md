## 📘 Documentazione Concettuale – Tabella `magazzino.inventari_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari](/dbzero/magazzino/tabelle/inventari)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Le righe di `magazzino.inventari`**: il dettaglio per articolo del documento.

---

### Si legge con la testata

Una riga da sola non ha contesto — data, magazzino e stato stanno in [magazzino.inventari](/dbzero/magazzino/tabelle/inventari). Il conteggio non modifica la giacenza: **produce una rettifica**, che a sua volta produce movimenti. È la catena che tiene il ledger come unica sorgente — anche una correzione da inventario resta una scrittura tracciata, non un ritocco.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
