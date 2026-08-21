## 📘 Documentazione Concettuale – Tabella `acquisti.ordini_righe`

> 👀 **Vedi anche**
>
> • [acquisti.ordini](/dbzero/acquisti/tabelle/ordini)
> • [acquisti.ordini_righe_fulfillment](/dbzero/acquisti/tabelle/ordini_righe_fulfillment)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Le righe dell'ordine di acquisto**: che cosa e quanto.

⭐ Portano lo **snapshot** di descrizione, unità di misura e IVA. Non sono ridondanza: l'ordine
deve restare leggibile com'era stato emesso anche se l'articolo cambia descrizione o aliquota.
È lo stesso principio degli snapshot in vendite.

Ci sono anche **campi di idempotenza**: servono a rendere ripetibile l'inserimento — un import
o un re-invio non devono duplicare le righe.

---

### ⚠️ Lo snapshot congela, ma non si aggiorna

Il rovescio dello snapshot vale qui come altrove: dopo la creazione, la riga **non segue** più
l'articolo. Se la descrizione a catalogo viene corretta, l'ordine continua a mostrare quella
vecchia — ed è corretto per un documento emesso, ma è la domanda che arriva dall'assistenza.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
