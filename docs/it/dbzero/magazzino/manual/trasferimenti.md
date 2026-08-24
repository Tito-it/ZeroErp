## 📘 Documentazione Concettuale – Tabella `magazzino.trasferimenti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.trasferimenti_righe](/dbzero/magazzino/tabelle/trasferimenti_righe)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Documento interno di **trasferimento fra magazzini**.

---

### Il ruolo nella catena

Genera **due** movimenti — `TRASF_OUT` e `TRASF_IN` — entrambi a impatto `none` sulla valorizzazione: spostare merce non ne cambia il valore complessivo, lo sposta. ⚠️ Il modello a due movimenti convive con la colonna `movimenti.magazzino_id_dest`, che suggerirebbe un movimento solo: quale delle due rappresentazioni valga è una decisione da prendere prima di attivare il dominio.

---

### ⚠️ Testata e righe

Il dettaglio sta in `magazzino.trasferimenti_righe`. Le due tabelle vanno lette insieme: la testata porta il contesto (data, magazzino, stato), le righe le quantità.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
