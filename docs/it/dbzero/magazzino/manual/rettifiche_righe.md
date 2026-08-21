## 📘 Documentazione Concettuale – Tabella `magazzino.rettifiche_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Le righe di `magazzino.rettifiche`**: il dettaglio per articolo del documento.

---

### Si legge con la testata

Una riga da sola non ha contesto — data, magazzino e stato stanno in [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche). È il ponte fra il conteggio e il ledger: le sue righe diventano movimenti con causale `RETT_POS` o `RETT_NEG`, entrambe a impatto `cmp` — una rettifica **cambia il valore di magazzino**, non solo la quantità.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
