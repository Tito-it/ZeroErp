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


### 🔄 rev 2026-09-13 — le date di consegna, con l'attore invertito

Due date nuove (`20260913-08`), facoltative: **`data_consegna_richiesta`** —
quando **noi** la chiediamo al fornitore — e
**`data_consegna_confermata_fornitore`** — quando **lui** conferma. È
l'informazione che mancava per sapere se la merce arriverà in tempo per una
consegna già promessa a un cliente. I nomi seguono la regola dei documenti
(non marcato = nostro, marcato = della controparte): rispetto a
`vendite.ordini_righe` sono **ribaltati**, e la vista di magazzino che leggerà
entrambe le tabelle non potrà confonderle. Nessun vincolo fra le due date.
Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 2.

---

{% include-markdown "signature-core.md" %}
