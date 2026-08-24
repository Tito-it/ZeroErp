## 📘 Documentazione Concettuale – Tabella `magazzino.trasferimenti_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Le righe di `magazzino.trasferimenti`**: il dettaglio per articolo del documento.

---

### Si legge con la testata

Una riga da sola non ha contesto — data, magazzino e stato stanno in [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti). Genera **due** movimenti — `TRASF_OUT` e `TRASF_IN` — entrambi a impatto `none` sulla valorizzazione: spostare merce non ne cambia il valore complessivo, lo sposta. ⚠️ Il modello a due movimenti convive con la colonna `movimenti.magazzino_id_dest`, che suggerirebbe un movimento solo: quale delle due rappresentazioni valga è una decisione da prendere prima di attivare il dominio.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
