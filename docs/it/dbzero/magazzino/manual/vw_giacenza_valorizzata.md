## 📘 Documentazione Concettuale – Vista `magazzino.vw_giacenza_valorizzata`

> 👀 **Vedi anche**
>
> • [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza)
> • [magazzino.vw_costo_medio](/dbzero/magazzino/views/vw_costo_medio)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

La giacenza con accanto **costo medio e valore**: `qta * costo_medio`, arrotondato a
`numeric(18,6)`.

È la vista che risponde a «quanto vale il mio magazzino».

---

### ⚠️ Il valore può essere `NULL`, e non è zero

Il costo medio arriva con un **`LEFT JOIN`** su `vw_costo_medio`. Se per quella coppia
articolo × magazzino non esiste una riga di costo — o se il costo medio è `NULL` perché la
quantità accumulata è zero — allora `costo_medio` è `NULL`, e `qta * NULL` è **`NULL`**.

⚠️ Conseguenza per chi somma: `sum(valore)` **ignora i NULL**, quindi un totale di magazzino
può risultare più basso del vero senza che nulla lo segnali. Prima di sommare va contato
quante righe hanno `costo_medio IS NULL`: sono merce presente ma non valorizzata.

Il `LEFT JOIN` è però la scelta giusta: con un `JOIN` interno quelle righe **sparirebbero**,
e la merce non valorizzata smetterebbe di comparire in giacenza.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
